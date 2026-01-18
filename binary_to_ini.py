
import sys
import os


TYPE_MAP, TYPE_SEQ, TYPE_STR, TYPE_INT, TYPE_FLOAT, TYPE_BOOL, TYPE_NULL = range(1, 8)



class BinaryReader:
    def __init__(self, data):
        self.data = data
        self.pos = 0
        self.len = len(data)

    def read_byte(self):
        if self.pos >= self.len:
            raise EOFError("Unexpected end of stream")
        b = self.data[self.pos]
        self.pos += 1
        return b

    def read_bytes(self, count):
        if self.pos + count > self.len:
            raise EOFError("Unexpected end of stream")
        res = self.data[self.pos : self.pos + count]
        self.pos += count
        return res

    def read_u32(self):
        b = self.read_bytes(4)
        return b[0] | (b[1] << 8) | (b[2] << 16) | (b[3] << 24)

    def read_i64(self):
        b = self.read_bytes(8)
        val = 0
        for i in range(8):
            val |= b[i] << (8 * i)
        if val & (1 << 63):
            val -= (1 << 64)
        return val

    def read_string(self):
        length = self.read_u32()
        b = self.read_bytes(length)
        return b.decode("utf-8")

def read_tlv(reader):
    if reader.pos >= reader.len:
        return None

    type_tag = reader.read_byte()

    if type_tag == TYPE_NULL:
        return None
    elif type_tag == TYPE_BOOL:
        val = reader.read_byte()
        return True if val == 1 else False
    elif type_tag == TYPE_INT:
        return reader.read_i64()
    elif type_tag == TYPE_FLOAT:
        hex_str = reader.read_string()
        return float.fromhex(hex_str)
    elif type_tag == TYPE_STR:
        return reader.read_string()
    elif type_tag == TYPE_SEQ:
        count = reader.read_u32()
        res = []
        for _ in range(count):
            res.append(read_tlv(reader))
        return res
    elif type_tag == TYPE_MAP:
        count = reader.read_u32()
        res = {}
        for _ in range(count):
            key_type = reader.read_byte()
            if key_type != TYPE_STR:
                raise ValueError("Map key must be string")
            key = reader.read_string()
            val = read_tlv(reader)
            res[key] = val
        return res
    else:
        raise ValueError(f"Unknown type tag: {type_tag}")

def parse_binary_data(data):
    reader = BinaryReader(data)
    return read_tlv(reader)


def format_ini_value(val):
    if val is None: return ""
    if isinstance(val, bool): return "true" if val else "false"
    if isinstance(val, list): return ", ".join(format_ini_value(x) for x in val)
    return str(val)

def dict_to_ini_section(data):
    """Рекурсивно преобразует словарь в INI-подобную структуру БЕЗ отступов"""
    lines = []
    
    for key, value in sorted(data.items()):
        if isinstance(value, dict):
            # Для вложенных словарей создаем подсекцию
            lines.append(f"[{key}]")
            lines.extend(dict_to_ini_section(value))
            lines.append("")  # пустая строка после секции
        elif isinstance(value, list):
            # Обработка списков каждый элемент в новой строке
            if value and isinstance(value[0], dict):
                # список словарей создаем пронумерованные подсекции
                for i, item in enumerate(value):
                    lines.append(f"[{key}.{i}]")
                    lines.extend(dict_to_ini_section(item))
                    lines.append("")
            else:
                # Простой список
                lines.append(f"{key} = {format_ini_value(value)}")
        else:
            lines.append(f"{key} = {format_ini_value(value)}")
    
    return lines

def dict_to_ini_schedule_days(data):
    lines = []

    schedules = data.get("schedule", {})

    DAY_ORDER = [
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    ]

    def day_index(day):
        try:
            return DAY_ORDER.index(day)
        except ValueError:
            return len(DAY_ORDER)  # плохие дни в конец

    for day in sorted(schedules.keys(), key=day_index):
        day_data = schedules[day]
        classes = day_data.get("class", {})

        lines.append("[schedule]")
        lines.append(f"day = {day}")
        lines.append("type = class")
        lines.append("")

        # сортировка занятий по времени
        for time in sorted(classes.keys()):
            lesson = classes[time]

            lines.append(f"time = {time}")

            for k, v in sorted(lesson.items()):
                if k == "type":
                    lines.append(f"lesson_type = {v}")
                else:
                    lines.append(f"{k} = {v}")

            lines.append("")

        if lines[-1] == "":
            lines.pop()
        lines.append("")

    if lines and lines[-1] == "":
        lines.pop()

    return "\n".join(lines)

def bin_to_ini_from_file(bin_path, ini_out_path):
    with open(bin_path, "rb") as f:
        raw_data = f.read()
    
    obj = parse_binary_data(raw_data)

    
    
    ini_text = dict_to_ini_schedule_days(obj)
    
    with open(ini_out_path, "w", encoding="utf-8") as f:
        f.write(ini_text)

if __name__ == "__main__":
    input_file = "output.bin"
    output_file = "output.ini"

    bin_to_ini_from_file(input_file, output_file)