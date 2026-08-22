from html import escape


def html_escape(value: object) -> str:
    return escape(str(value), quote=True)
