#!/usr/bin/env python3
"""vio_sqm.py — lee y escribe mission.sqm de Eden (texto, version=54) sin perder nada.

Cada sentencia (clase o asignación) guarda su texto original exacto, desde el comienzo de su línea hasta
el salto de línea después del ';'. Al escribir:
  - lo que no se tocó sale tal cual, byte a byte;
  - las clases nuevas o cambiadas se escriben en formato Eden: tabuladores, CRLF, "class X" / "{" / "};";
  - las asignaciones nuevas o cambiadas salen en una línea: key=valor; (arreglos en línea {a,b,c}).
Los textos se leen como latin-1 para que cualquier byte vuelva igual.

Uso como módulo:  root = parse(texto); ... ; texto = dump(root)
Uso directo:      vio_sqm.py roundtrip <mission.sqm> ...   (comprueba que leer y escribir da lo mismo)
"""
import sys

NL = "\r\n"


class Asg:
    """Asignación key=valor; (key sin '[]'; arr=True si era key[]=)."""
    __slots__ = ("key", "arr", "value", "raw", "dirty")

    def __init__(self, key, value, arr=False, raw=None):
        self.key, self.value, self.arr, self.raw = key, value, arr, raw
        self.dirty = raw is None


class Cls:
    """class nombre { ... };"""
    __slots__ = ("name", "items", "raw", "dirty")

    def __init__(self, name, items=None, raw=None):
        self.name, self.items, self.raw = name, list(items or []), raw
        self.dirty = raw is None

    # --- consultas ---
    def cls(self, name):
        for it in self.items:
            if isinstance(it, Cls) and it.name == name:
                return it
        return None

    def classes(self):
        return [it for it in self.items if isinstance(it, Cls)]

    def asg(self, key):
        for it in self.items:
            if isinstance(it, Asg) and it.key == key:
                return it
        return None

    def get(self, key, default=None):
        a = self.asg(key)
        return default if a is None else a.value

    # --- cambios (marcan la clase para reescribirla) ---
    def set(self, key, value, arr=None):
        a = self.asg(key)
        if a is None:
            self.items.append(Asg(key, value, bool(arr)))
            self.dirty = True
        else:
            a.value, a.dirty = value, True
            if arr is not None:
                a.arr = arr
        return self

    def remove(self, key):
        n = len(self.items)
        self.items = [it for it in self.items if not (isinstance(it, Asg) and it.key == key)]
        if len(self.items) != n:
            self.dirty = True


class Raw(str):
    """Valor que se escribe tal cual (p. ej. un número ya formateado)."""


# ---------------------------------------------------------------- lectura

class _P:
    def __init__(self, s):
        self.s, self.i, self.n = s, 0, len(s)

    def err(self, msg):
        line = self.s.count("\n", 0, self.i) + 1
        raise SyntaxError(f"mission.sqm línea {line}: {msg}: {self.s[self.i:self.i + 40]!r}")

    def ws(self):
        s, i, n = self.s, self.i, self.n
        while i < n and s[i] in " \t\r\n":
            i += 1
        self.i = i

    def line_start(self, pos):
        return self.s.rfind("\n", 0, pos) + 1

    def ident(self):
        s, i = self.s, self.i
        j = i
        while j < self.n and (s[j].isalnum() or s[j] == "_"):
            j += 1
        if j == i:
            self.err("se esperaba un nombre")
        self.i = j
        return s[i:j]

    def expect(self, ch):
        self.ws()
        if self.s.startswith(ch, self.i):
            self.i += len(ch)
        else:
            self.err(f"se esperaba {ch!r}")

    def end_of_line(self):
        """Consume espacios y el salto de línea tras ';' (si lo hay) y devuelve la posición final."""
        s, i = self.s, self.i
        while i < self.n and s[i] in " \t":
            i += 1
        if s.startswith("\r\n", i):
            i += 2
        elif i < self.n and s[i] == "\n":
            i += 1
        self.i = i
        return i

    def string(self):
        s = self.s
        out = []
        while True:
            assert s[self.i] == '"'
            i = self.i + 1
            buf = []
            while True:
                j = s.find('"', i)
                if j < 0:
                    self.err("texto sin cerrar")
                buf.append(s[i:j])
                if s.startswith('""', j):
                    buf.append('"')
                    i = j + 2
                    continue
                self.i = j + 1
                break
            out.append("".join(buf))
            # "a" \n "b": texto de varias líneas
            k = self.i
            while k < self.n and s[k] in " \t":
                k += 1
            if s.startswith("\\n", k):
                k += 2
                while k < self.n and s[k] in " \t":
                    k += 1
                if k < self.n and s[k] == '"':
                    self.i = k
                    continue
            return "\n".join(out)

    def value(self):
        self.ws()
        s, i = self.s, self.i
        c = s[i] if i < self.n else ""
        if c == '"':
            return self.string()
        if c == "{":
            self.i += 1
            arr = []
            while True:
                self.ws()
                if self.s[self.i] == "}":
                    self.i += 1
                    return arr
                arr.append(self.value())
                self.ws()
                if self.s[self.i] == ",":
                    self.i += 1
        j = i
        while j < self.n and s[j] not in ",;}\r\n":
            j += 1
        tok = s[i:j].strip()
        if not tok:
            self.err("valor vacío")
        self.i = j
        try:
            return int(tok)
        except ValueError:
            pass
        try:
            return float(tok)
        except ValueError:
            return Raw(tok)

    def block(self, closing):
        items = []
        while True:
            self.ws()
            if self.i >= self.n:
                if closing:
                    self.err("falta '}'")
                return items
            if self.s[self.i] == "}":
                if not closing:
                    self.err("'}' de más")
                return items
            start = self.line_start(self.i)
            word = self.ident()
            if word == "class":
                self.ws()
                name = self.ident()
                self.expect("{")
                inner = self.block(True)
                self.expect("}")
                self.expect(";")
                end = self.end_of_line()
                items.append(Cls(name, inner, raw=self.s[start:end]))
            else:
                arr = self.s.startswith("[]", self.i)
                if arr:
                    self.i += 2
                self.expect("=")
                val = self.value()
                self.expect(";")
                end = self.end_of_line()
                items.append(Asg(word, val, arr, raw=self.s[start:end]))


def parse(text):
    """Texto de mission.sqm -> Cls raíz (nombre vacío)."""
    p = _P(text)
    root = Cls("", p.block(False), raw="")
    root.dirty = False
    return root


# ---------------------------------------------------------------- escritura

def fmt(v):
    if isinstance(v, Raw):
        return str(v)
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        if v == int(v) and abs(v) < 1e15:
            return str(int(v))
        return "%.8g" % v
    if isinstance(v, str):
        parts = [p.replace('"', '""') for p in v.split("\n")]
        return '"' + '" \\n "'.join(parts) + '"'
    if isinstance(v, (list, tuple)):
        return "{" + ",".join(fmt(x) for x in v) + "}"
    raise TypeError(f"no sé escribir {type(v).__name__}")


def _clean(c):
    if c.dirty or c.raw is None:
        return False
    return all((not it.dirty) if isinstance(it, Asg) else _clean(it) for it in c.items)


def _dump(items, depth, out):
    ind = "\t" * depth
    for it in items:
        if isinstance(it, Asg):
            if it.dirty or it.raw is None:
                out.append(f"{ind}{it.key}{'[]' if it.arr else ''}={fmt(it.value)};{NL}")
            else:
                out.append(it.raw)
        elif _clean(it):
            out.append(it.raw)
        else:
            out.append(f"{ind}class {it.name}{NL}{ind}{{{NL}")
            _dump(it.items, depth + 1, out)
            out.append(f"{ind}}};{NL}")


def dump(root):
    out = []
    _dump(root.items, 0, out)
    return "".join(out)


def mark_all(root):
    """Marca todas las clases para reescribirlas (las asignaciones conservan su texto). Para las pruebas."""
    stack = [root]
    while stack:
        c = stack.pop()
        c.dirty = c is not root
        stack.extend(c.classes())


def roundtrip(text):
    """True si leer y escribir devuelve el mismo texto, tanto copiando como reescribiendo todas las clases."""
    root = parse(text)
    if dump(root) != text:
        return False
    mark_all(root)
    return dump(root) == text


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "roundtrip":
        bad = 0
        for f in sys.argv[2:]:
            t = open(f, "rb").read().decode("latin-1")
            ok = roundtrip(t)
            bad += not ok
            print(f"{'OK ' if ok else 'MAL'} {f}")
        sys.exit(1 if bad else 0)
    sys.exit(__doc__)
