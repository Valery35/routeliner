"""Извлечение русских строк интерфейса из исходников (для таблицы переводов)."""
import ast, glob, re, json
CYR = re.compile("[А-Яа-яЁё]")
def fold(n):
    if isinstance(n, ast.Constant) and isinstance(n.value, str):
        return n.value
    if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Add):
        a, b = fold(n.left), fold(n.right)
        if a is not None and b is not None:
            return a + b
    return None
def extract(root="routeliner"):
  keys = {}
  for f in sorted(glob.glob(root + "/**/*.py", recursive=True)):
      if f.endswith("translations.py"): continue
      tree = ast.parse(open(f, encoding="utf-8").read())
      doc = set()
      for node in ast.walk(tree):
          if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef)) and node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant):
              doc.add(id(node.body[0].value))
      seen_inner = set()
      for node in ast.walk(tree):
          if isinstance(node, ast.BinOp):
              v = fold(node)
              if v is not None:
                  for c in ast.walk(node):
                      seen_inner.add(id(c))
                  if CYR.search(v): keys.setdefault(v, f)
      for node in ast.walk(tree):
          if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in doc and id(node) not in seen_inner and CYR.search(node.value):
              keys.setdefault(node.value, f)
  return keys


SKIP_PREFIX = ("ПК ", "^(", "https://")
SKIP = {"ПК ", "пк", "км", "км ", " ПК ", "исполнительная"}


def ui_keys(root="routeliner"):
    return [k for k in extract(root) if k not in SKIP and not k.startswith(SKIP_PREFIX)]
