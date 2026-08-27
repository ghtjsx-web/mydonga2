"""
langchain_classic.agents 모듈
클래식 LangChain AgentExecutor 및 핵심 에이전트 클래스 구현체
"""

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool


@dataclass
class AgentAction:
    """에이전트가 실행할 단일 도구 액션 정보"""
    tool: str
    tool_input: Union[str, dict]
    log: str = ""
    tool_call_id: str = ""


@dataclass
class AgentFinish:
    """에이전트 최종 완료 결과"""
    return_values: Dict[str, Any]
    log: str = ""


class AgentExecutor:
    """
    [langchain_classic AgentExecutor 완전 호환 클래스]
    
    속성:
        agent: 에이전트 런너블 (Runnable)
        tools: 도구 리스트 (Sequence[BaseTool])
        return_intermediate_steps: 실행 단계 로깅 여부 (기본 True)
        max_iterations: 최대 루프 반복 수 (기본 15)
        max_execution_time: 최대 실행 허용 시간(초)
        early_stopping_method: 조기 종료 방식 ('force' 또는 'generate')
        verbose: 디버깅 콘솔 출력 여부
        handle_parsing_errors: 도구 실행 오류 예외 처리 여부
    """
    def __init__(
        self,
        agent: Optional[Runnable] = None,
        tools: Optional[Sequence[BaseTool]] = None,
        model: Optional[Any] = None,
        system_prompt: str = "당신은 도구(Tool)를 사용하여 사용자의 질문에 정확하게 답하는 AI 어시스턴트입니다.",
        return_intermediate_steps: bool = True,
        max_iterations: int = 15,
        max_execution_time: Optional[float] = None,
        early_stopping_method: str = "force",
        verbose: bool = False,
        handle_parsing_errors: bool = True,
        **kwargs: Any
    ):
        self.tools = list(tools) if tools else []
        self.tools_dict: Dict[str, BaseTool] = {t.name: t for t in self.tools}
        self.model = model
        self.system_prompt = system_prompt
        self.return_intermediate_steps = return_intermediate_steps
        self.max_iterations = max_iterations
        self.max_execution_time = max_execution_time
        self.early_stopping_method = early_stopping_method
        self.verbose = verbose
        self.handle_parsing_errors = handle_parsing_errors
        self.extra_kwargs = kwargs

        # agent 런너블 구성
        if agent is not None:
            self.agent = agent
        elif self.model is not None:
            model_with_tools = self.model.bind_tools(self.tools)
            prompt = ChatPromptTemplate.from_messages([
                ("system", self.system_prompt),
                MessagesPlaceholder(variable_name="chat_history"),
                ("user", "{input}")
            ])
            self.agent = prompt | model_with_tools
        else:
            raise ValueError("AgentExecutor 생성 시 'agent' 또는 'model'과 'tools'가 제공되어야 합니다.")

    @classmethod
    def from_agent_and_tools(
        cls,
        agent: Runnable,
        tools: Sequence[BaseTool],
        verbose: bool = False,
        return_intermediate_steps: bool = True,
        max_iterations: int = 15,
        **kwargs: Any
    ) -> "AgentExecutor":
        """클래식 팩토리 메서드: agent와 tools로부터 AgentExecutor 생성"""
        return cls(
            agent=agent,
            tools=tools,
            verbose=verbose,
            return_intermediate_steps=return_intermediate_steps,
            max_iterations=max_iterations,
            **kwargs
        )

    def _log(self, message: str) -> None:
        """verbose 모드 출력"""
        if self.verbose:
            print(f"[AgentExecutor] {message}")

    def invoke(self, inputs: Union[Dict[str, Any], str], **kwargs: Any) -> Dict[str, Any]:
        """
        AgentExecutor 메인 실행 루프
        - 입력 정규화
        - 도구 호출 루프 (max_iterations, max_execution_time 검사)
        - intermediate_steps (AgentAction, Tool Output) 로깅
        - 최종 응답(output) 반환
        """
        start_time = time.time()
        
        if isinstance(inputs, str):
            user_input = inputs
            chat_history: List[BaseMessage] = []
        else:
            user_input = inputs.get("input") or inputs.get("question", "")
            chat_history = inputs.get("chat_history", [])

        self._log(f"입력 수신: {user_input}")

        intermediate_steps: List[Dict[str, Any]] = []
        classic_steps: List[Tuple[AgentAction, str]] = []
        iteration = 0

        # 1. 초기 에이전트 추론
        ai_message: AIMessage = self.agent.invoke({
            "input": user_input,
            "chat_history": chat_history
        })

        # 2. 도구 호출 루프
        if ai_message.tool_calls:
            execution_messages: List[BaseMessage] = [
                SystemMessage(content=self.system_prompt),
                *chat_history,
                HumanMessage(content=user_input),
                ai_message
            ]

            while ai_message.tool_calls and iteration < self.max_iterations:
                # 실행 시간 초과 검사
                if self.max_execution_time and (time.time() - start_time) > self.max_execution_time:
                    self._log("최대 실행 시간 초과로 조기 종료합니다.")
                    break

                iteration += 1
                self._log(f"반복 {iteration}/{self.max_iterations}: 도구 호출 {len(ai_message.tool_calls)}건 감지")

                for tool_call in ai_message.tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]
                    tool_id = tool_call.get("id", "")

                    action = AgentAction(
                        tool=tool_name,
                        tool_input=tool_args,
                        log=f"Calling tool `{tool_name}` with args {tool_args}",
                        tool_call_id=tool_id
                    )

                    target_tool = self.tools_dict.get(tool_name)
                    if target_tool:
                        try:
                            tool_output = target_tool.invoke(tool_args)
                        except Exception as e:
                            if self.handle_parsing_errors:
                                tool_output = f"도구 실행 오류: {str(e)}"
                            else:
                                raise e
                    else:
                        tool_output = f"❌ [{tool_name}] 등록되지 않은 도구입니다."

                    self._log(f"도구 실행 완료: {tool_name} -> {tool_output}")

                    # 로그 누적
                    classic_steps.append((action, str(tool_output)))
                    intermediate_steps.append({
                        "iteration": iteration,
                        "tool": tool_name,
                        "args": tool_args,
                        "output": str(tool_output)
                    })

                    execution_messages.append(
                        ToolMessage(content=str(tool_output), tool_call_id=tool_id)
                    )

                # 피드백 반영 후 다음 단계 추론
                if self.model:
                    final_ai_msg = self.model.invoke(execution_messages)
                    ai_message = final_ai_msg
                else:
                    break

            output_text = ai_message.content or "답변 생성을 완료했습니다."
        else:
            output_text = ai_message.content or "답변을 생성할 수 없습니다."

        finish = AgentFinish(
            return_values={"output": output_text},
            log=output_text
        )

        result: Dict[str, Any] = {
            "input": user_input,
            "output": finish.return_values["output"]
        }

        if self.return_intermediate_steps:
            result["intermediate_steps"] = intermediate_steps
            result["classic_steps"] = classic_steps

        return result

    def run(self, query: str, **kwargs: Any) -> str:
        """단일 쿼리 실행 편의 메서드"""
        res = self.invoke({"input": query}, **kwargs)
        return res.get("output", "")


__all__ = ["AgentExecutor", "AgentAction", "AgentFinish"]
