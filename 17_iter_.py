my_list = [10, 20, 30, 40, 50]
print(my_list)
print()
my_iterator = iter(my_list) #  iter() 함수를 사용하여 이터레이터(Iterator)로 변환
print(next(my_iterator))  # 출력: 10 next() 함수를 호출하여 값을 하나씩 꺼냄
print(next(my_iterator))  # 출력: 20
print(next(my_iterator))  # 출력: 30
print(next(my_iterator))  # 출력: 40
print(next(my_iterator))  # 출력: 50
print()

class CountUp:
    def __init__(self, limit):
        self.limit = limit  
        self.current = 0    


    def __iter__(self):
        return self  #이터레이터 객체 자기 자신을 반환해야 합니다.

    def __next__(self):
        if self.current < self.limit:
            self.current += 1
            return self.current  
        else:
            raise StopIteration # raise는 강제로 예외(Exception)를 발생시키는 명령어



counter = CountUp(5)
for num in counter:
    print(num)
