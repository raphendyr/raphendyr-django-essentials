import logging
from copy import copy
from django.core.management.color import color_style
from django.utils.termcolors import make_style


class SourceColorizeFormatter(logging.Formatter):
    def __init__(self, *args, **kwargs):
        color_conf = kwargs.pop('colors', None)
        super().__init__(*args, **kwargs)
        style = color_style()
        self.mapping = self.create_mapping(style, color_conf)

    def create_mapping(self, style, conf):
        mapping = {}
        for name, val in conf.items():
            if isinstance(val, dict):
                style_func = make_style(**val)
            else:
                style_func = getattr(style, val, None)

            if style_func:
                mapping[name] = style_func

        return mapping

    def format(self, record):
        name = record.name
        possible = [(len(k), k, f) for k, f in self.mapping.items() if name.startswith(k)]
        if possible:
            record = copy(record)
            colorizer = max(possible)[2]
            record.msg = colorizer(record.msg)
        return super().format(record)
