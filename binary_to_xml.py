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
        res = self.data[self.pos:self.pos + count]
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

# TlV парер

def read_tlv(reader):
    if reader.pos >= reader.len:
        return None

    type_tag = reader.read_byte()

    if type_tag == TYPE_NULL:
        return None
    elif type_tag == TYPE_BOOL:
        return reader.read_byte() == 1
    elif type_tag == TYPE_INT:
        return reader.read_i64()
    elif type_tag == TYPE_FLOAT:
        hex_str = reader.read_string()
        return float.fromhex(hex_str)
    elif type_tag == TYPE_STR:
        return reader.read_string()
    elif type_tag == TYPE_SEQ:
        count = reader.read_u32()
        return [read_tlv(reader) for _ in range(count)]
    elif type_tag == TYPE_MAP:
        count = reader.read_u32()
        res = {}
        for _ in range(count):
            key_type = reader.read_byte()
            if key_type != TYPE_STR:
                raise ValueError("Map key must be string")
            key = reader.read_string()
            res[key] = read_tlv(reader)
        return res
    else:
        raise ValueError(f"Unknown type tag: {type_tag}")

def parse_binary_data(data):
    reader = BinaryReader(data)
    return read_tlv(reader)

# xml 

def xml_escape(text):
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
    )

def is_valid_xml_name(name):
    if not name:
        return False
    if not (name[0].isalpha() or name[0] == "_"):
        return False
    for c in name:
        if not (c.isalnum() or c in "_-"):
            return False
    return True


def python_to_xml_lines(key, value, indent=0):
    space = "  " * indent
    lines = []

    # --- dict ---
    if isinstance(value, dict):
        if is_valid_xml_name(key):
            lines.append(f"{space}<{key}>")
            for k, v in value.items():
                lines.extend(python_to_xml_lines(k, v, indent + 1))
            lines.append(f"{space}</{key}>")
        else:
            lines.append(f'{space}<item key="{xml_escape(key)}">')
            for k, v in value.items():
                lines.extend(python_to_xml_lines(k, v, indent + 1))
            lines.append(f"{space}</item>")

    # list
    elif isinstance(value, list):
        tag = key if is_valid_xml_name(key) else "list"
        lines.append(f"{space}<{tag}>")
        for item in value:
            lines.extend(python_to_xml_lines("item", item, indent + 1))
        lines.append(f"{space}</{tag}>")

    # primitiv
    else:
        tag = key if is_valid_xml_name(key) else "value"
        if value is None:
            lines.append(f'{space}<{tag} null="true" />')
        else:
            lines.append(
                f"{space}<{tag}>{xml_escape(str(value))}</{tag}>"
            )

    return lines

def dict_to_xml(data, root_name="data"):
    lines = []
    lines.append(f"<{root_name}>")

    for key, value in data.items():
        lines.extend(python_to_xml_lines(key, value, indent=1))

    lines.append(f"</{root_name}>")
    return "\n".join(lines)



def bin_to_xml_from_file(bin_path, xml_out_path):
    with open(bin_path, "rb") as f:
        raw_data = f.read()

    obj = parse_binary_data(raw_data)

    xml_text = dict_to_xml(obj)

    with open(xml_out_path, "w", encoding="utf-8") as f:
        f.write(xml_text)


if __name__ == "__main__":
    input_file = "output.bin"
    output_file = "output.xml"

    bin_to_xml_from_file(input_file, output_file)
