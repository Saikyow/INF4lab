import hcl2  
import os
import sys
import time 

TYPE_MAP, TYPE_SEQ, TYPE_STR, TYPE_INT, TYPE_FLOAT, TYPE_BOOL, TYPE_NULL = range(1, 8)

def write_u32(buf, n):
    for i in range(4):
        buf.append((n >> (8*i)) & 0xFF)

def write_i64(buf, n):
    if n < 0: n = (1 << 64) + n
    for i in range(8):
        buf.append((n >> (8*i)) & 0xFF)

def write_string(buf, s):
    b = str(s).encode("utf-8")
    write_u32(buf, len(b))
    buf.extend(b)

def write_tlv(buf, obj):
    if obj is None:
        buf.append(TYPE_NULL)
    elif isinstance(obj, bool):
        buf.append(TYPE_BOOL)
        buf.append(1 if obj else 0)
    elif isinstance(obj, int):
        buf.append(TYPE_INT)
        write_i64(buf, obj)
    elif isinstance(obj, float):
        buf.append(TYPE_FLOAT)
        write_string(buf, float.hex(obj))
    elif isinstance(obj, str):
        buf.append(TYPE_STR)
        write_string(buf, obj)
    elif isinstance(obj, list):
        buf.append(TYPE_SEQ)
        write_u32(buf, len(obj))
        for x in obj: write_tlv(buf, x)
    elif isinstance(obj, dict):
        buf.append(TYPE_MAP)
        write_u32(buf, len(obj))
        for k, v in obj.items():
            buf.append(TYPE_STR)
            write_string(buf, k)
            write_tlv(buf, v)
def run_benchmark(input_path, iterations=100):
    if not os.path.exists(input_path):
        return

    with open(input_path, 'r', encoding='utf-8') as f:
        text_content = f.read()

    print(f"Запуск теста производительности для hcl2 ({iterations} итераций)")
    
    start_time = time.perf_counter()
    
    for _ in range(iterations):
        data = hcl2.loads(text_content) 
        buf = bytearray()
        write_tlv(buf, data)
        _ = bytes(buf)

    end_time = time.perf_counter()
    total_time = end_time - start_time

  
    print(f"Результат (библиотека hcl2):")
    print(f"Общее время за 100 циклов: {total_time:.6f} сек.")
    print(f"Среднее время за 1 цикл: {total_time/iterations:.6f} сек.")




def convert_hcl_to_bin(input_path, output_path):
    # используем либу hcl2 для чтения 
    with open(input_path, 'r', encoding='utf-8') as f:
        data = hcl2.load(f)
    
    # Сериализуем полученный словарь в байты
    buf = bytearray()
    write_tlv(buf, data)
    
    # Сохраняем результат
    with open(output_path, 'wb') as f:
        f.write(buf)

if __name__ == "__main__":
    inp, outp = "input.hcl", "output2.bin"
    if os.path.exists(inp):
        try:
            convert_hcl_to_bin(inp, outp)
            print(f"Готово! Файл {outp} создан.")
            run_benchmark(inp, 100)
        except Exception as e:
            print(f"Ошибка: {e}")
    else:
        print(f"Файл {inp} не найден.")