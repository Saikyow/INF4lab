import sys
import os
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
    b = s.encode("utf-8")
    write_u32(buf, len(b))
    buf.extend(b)

def write_tlv(buf, obj):
    if obj is None:
        buf.append(TYPE_NULL); return
    if obj is True or obj is False:
        buf.append(TYPE_BOOL); buf.append(1 if obj else 0); return
    if isinstance(obj, int):
        buf.append(TYPE_INT); write_i64(buf, obj); return
    if isinstance(obj, float):
        buf.append(TYPE_FLOAT); write_string(buf, obj.hex()); return
    if isinstance(obj, str):
        buf.append(TYPE_STR); write_string(buf, obj); return
    if isinstance(obj, list):
        buf.append(TYPE_SEQ)
        write_u32(buf, len(obj))
        for x in obj: write_tlv(buf, x)
        return
    if isinstance(obj, dict):
        buf.append(TYPE_MAP)
        write_u32(buf, len(obj))
        for k, v in obj.items():
            buf.append(TYPE_STR)
            write_string(buf, k)
            write_tlv(buf, v)
        return

# Парсер

class Tokenizer:
    def __init__(self, text):
        self.text = text
        self.pos = 0
        self.len = len(text)

    def peek_char(self):
        return self.text[self.pos] if self.pos < self.len else None

    def next_char(self):
        ch = self.peek_char()
        if ch: self.pos += 1
        return ch

    def skip_whitespace(self):
        while True:
            ch = self.peek_char()
            if ch is None: break
            if ch in ' \t\n\r':
                self.next_char()
            elif ch == '#' or (ch == '/' and self.pos + 1 < self.len and self.text[self.pos+1] == '/'):
                while self.peek_char() not in ['\n', '\r', None]:
                    self.next_char()
            else:
                break

    def get_token(self):
        self.skip_whitespace()
        ch = self.peek_char()
        if ch is None: return None

        if ch in '{}=[],':
            return self.next_char()

        if ch == '"':
            self.next_char()
            res = ""
            while True:
                c = self.next_char()
                if c is None: raise ValueError("Unclosed string")
                if c == '"': break
                res += c
            return res

        res = ""
        while True:
            ch = self.peek_char()
            if ch is None or ch in ' \t\n\r{}=[],"#':
                break
            res += self.next_char()
        
        if res == "true": return True
        if res == "false": return False
        if res == "null": return None
        
        if res.isdigit() or (res.startswith('-') and res[1:].isdigit()):
            return int(res)
        try:
            return float(res)
        except:
            pass
        return res

class HCLParser:
    def __init__(self, text):
        self.tok = Tokenizer(text)
        self.lookahead = self.tok.get_token()

    def consume(self):
        val = self.lookahead
        self.lookahead = self.tok.get_token()
        return val

    def peek(self):
        return self.lookahead

    def parse_value(self):
        token = self.peek()
        if token == '{': return self.parse_object()
        elif token == '[': return self.parse_list()
        else: return self.consume()

    def parse_list(self):
        self.consume()
        res = []
        while self.peek() != ']':
            if self.peek() is None: raise ValueError("Unexpected EOF in list")
            res.append(self.parse_value())
            if self.peek() == ',':
                self.consume()
        self.consume()
        return res

    def parse_object(self):
        self.consume()
        obj = {}
        while self.peek() != '}' and self.peek() is not None:
            self.parse_key_value(obj)
        if self.peek() == '}':
            self.consume()
        return obj

    def parse_key_value(self, current_dict):
        key = self.consume()
        nxt = self.peek()

        if nxt == '=':
            self.consume()
            current_dict[key] = self.parse_value()
            if self.peek() == ',': self.consume()

        elif nxt == '{':
            if key not in current_dict: current_dict[key] = {}
            val = self.parse_object()
            current_dict[key] = val

        elif isinstance(nxt, str) and nxt not in ['=', '{', '[', ']', '}']:
            target = current_dict
            if key not in target: target[key] = {}
            target = target[key]

            while self.peek() != '{' and self.peek() is not None:
                label = self.consume()
                if self.peek() == '{':
                    if label not in target: target[label] = {}
                    if not isinstance(target[label], dict): target[label] = {}
                    block_body = self.parse_object()
                    target[label] = block_body
                    return
                else:
                    if label not in target: target[label] = {}
                    target = target[label]
        else:
            raise ValueError(f"Unexpected token after key '{key}': {nxt}")

    def parse_root(self):
        obj = {}
        while self.peek() is not None:
            self.parse_key_value(obj)
        return obj

def parse_hcl(text):
    parser = HCLParser(text)
    return parser.parse_root()

def hcl_to_bin_from_file(path):

    with open("input.hcl", "r", encoding="utf-8") as f:
        text = f.read()
    # Парсим текст в структуру Python
    obj = parse_hcl(text)
    
    # Конвертируем структуру в байты
    buf = bytearray()
    write_tlv(buf, obj)
    return bytes(buf)
def run_benchmark(input_path, iterations=100):
    if not os.path.exists(input_path):
        print(f"Ошибка: Файл {input_path} не найден для теста.")
        return

    with open(input_path, "r", encoding="utf-8") as f:
        text = f.read()

    print(f"Запуск замера времени для {iterations} итераций")
    
    start_time = time.perf_counter()
    
    for i in range(iterations):
    
        obj = parse_hcl(text)
        buf = bytearray()
        write_tlv(buf, obj)
        _ = bytes(buf) 

    end_time = time.perf_counter()
    total_time = end_time - start_time


    print(f"Результат теста своей реализации")
    print(f"Общее время: {total_time:.6f} сек.")
    print(f"Среднее время на 1 цикл: {total_time/iterations:.6f} сек.")



if __name__ == "__main__":
    input_filename = "input.hcl"
    output_filename = "output.bin"

    # Проверка на сщуествование 
    if not os.path.exists(input_filename):
        print(f"Ошибка: Файл '{input_filename}' не найден в текущей директории.")
        sys.exit(1)

    try:
        print(f"Чтение {input_filename}")
        
        # Конвертация
        binary_data = hcl_to_bin_from_file(input_filename)
        

        with open(output_filename, "wb") as f:
            f.write(binary_data)
            
        print(f"Данные сохранены в {output_filename}")
        # тест на скорость 
        run_benchmark(input_filename, 100)

    except Exception as e:
        print(f"Произошла ошибка при конвертации: {e}")