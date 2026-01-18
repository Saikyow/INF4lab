import struct


TYPE_MAP, TYPE_SEQ, TYPE_STR, TYPE_INT, TYPE_FLOAT, TYPE_BOOL, TYPE_NULL = range(1, 8)

class BinDecoder:
    def __init__(self, data):
        self.data = data
        self.pos = 0

    def read_u32(self):
        res = int.from_bytes(self.data[self.pos:self.pos+4], 'little')
        self.pos += 4
        return res

    def read_string(self):
        length = self.read_u32()
        res = self.data[self.pos:self.pos+length].decode('utf-8')
        self.pos += length
        return res

    def decode_next(self):
        t = self.data[self.pos]
        self.pos += 1
        
        if t == TYPE_STR: return self.read_string()
        if t == TYPE_INT:
            res = int.from_bytes(self.data[self.pos:self.pos+8], 'little')
            self.pos += 8
            return res
        if t == TYPE_SEQ:
            count = self.read_u32()
            return [self.decode_next() for _ in range(count)]
        if t == TYPE_MAP:
            count = self.read_u32()
            obj = {}
            for _ in range(count):
                self.pos += 1 # Пропускаем маркер TYPE_STR 
                key = self.read_string()
                obj[key] = self.decode_next()
            return obj
        return None

def write_pretty_ini(data, filename):
    with open(filename, 'w', encoding='utf-8') as f:
        for root_key, root_value in data.items():
            
            if isinstance(root_value, list):
                for item in root_value:
                    f.write(f"[{root_key}]\n") #  заголовок [schedule]
                    for k, v in item.items():
                        f.write(f"{k} = {v}\n") # Печатаем пары без кавычек
                    f.write("\n") # Пустая строка между блоками
            
            # Если просто одиночный объект
            elif isinstance(root_value, dict):
                f.write(f"[{root_key}]\n")
                for k, v in root_value.items():
                    f.write(f"{k} = {v}\n")
                f.write("\n")


try:
    with open("output.bin", "rb") as f:
        content = f.read()
    
    decoder = BinDecoder(content)
    parsed_data = decoder.decode_next()
    
    write_pretty_ini(parsed_data, "result.ini")
    print("Файл result.ini успешно создан в красивом виде!")
except Exception as e:
    print(f"Ошибка: {e}")
