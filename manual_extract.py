from jinja2 import Environment
from babel.messages.extract import extract_from_file
from jinja2.ext import babel_extract

def extract_translations(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        source = f.read()
    env = Environment(extensions=['jinja2.ext.i18n'])
    options = {
        'silent': False,
        'trim_blocks': True,
        'lstrip_blocks': True,
        'extensions': ['jinja2.ext.i18n'],
    }
    return babel_extract(env, source, ['_'], options)

filename = 'templates/reports.html'  # Ajusta esta ruta si es necesario
for lineno, funcname, message, comments in extract_translations(filename):
    print(f"Línea {lineno}: {message}")