# -*- coding: utf-8 -*-
"""Проверка схем компоновки (Template.dcs), правленных мимо конструктора.

EDT такие схемы валидирует чисто, а платформа падает при загрузке в базу
("Исключение XDTO при чтении Template.xml ... Тип: anyType"). Скрипт ищет:
  1. <title> без xsi:type (и другие узлы с локализованной строкой из списка ниже);
  2. разнобой у однотипных узлов внутри одного файла: если 40 узлов <title> идут с xsi:type,
     а два без атрибутов вовсе, эти два почти наверняка написаны руками
     (xs:string у части узлов в типовых схемах встречается штатно, это не замечание);
  3. <appearance> внутри поля набора данных не последним элементом (порядок по XSD).

Запуск:
  python check_dcs_nodes.py <папка с отчетами или файл Template.dcs>
"""
import io
import os
import re
import sys
from collections import Counter

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

LOCALIZED = ('title', 'presentation')   # узлы, которым нужен xsi:type="v8:LocalStringType"


def files(root):
    if os.path.isfile(root):
        yield root
        return
    for folder, _, names in os.walk(root):
        for name in names:
            if name == 'Template.dcs':
                yield os.path.join(folder, name)


def check(path):
    text = open(path, encoding='utf-8').read()
    problems = []

    for tag in LOCALIZED:
        # открывающие теги с содержимым <v8:item>: у них должен быть тип
        for m in re.finditer(r'<%s(\s[^>]*)?>\s*<v8:item>' % tag, text):
            attrs = m.group(1) or ''
            if 'xsi:type' not in attrs:
                line = text.count('\n', 0, m.start()) + 1
                problems.append('стр. %d: <%s> без xsi:type' % (line, tag))

    # разнобой атрибутов однотипных узлов
    for tag in LOCALIZED:
        variants = Counter(re.findall(r'<%s(?:\s[^>]*)?>' % tag, text))
        if len(variants) > 1 and ('<%s>' % tag) in variants:
            listing = ', '.join('%s x%d' % (k, v) for k, v in variants.most_common())
            problems.append('разные варианты <%s>: %s' % (tag, listing))

    # appearance последним в блоке поля
    for block in re.finditer(r'<field xsi:type="DataSetField[^"]*">(.*?)\n[ \t]*</field>[ \t]*$',
                             text, re.S | re.M):
        body = block.group(1)
        pos = body.find('<appearance>')
        if pos >= 0 and re.search(r'<(field|title|dataPath)>', body[body.find('</appearance>'):]):
            line = text.count('\n', 0, block.start()) + 1
            problems.append('стр. %d: <appearance> не последний в поле набора' % line)
    return problems


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    total = bad = 0
    for path in files(sys.argv[1]):
        total += 1
        problems = check(path)
        if problems:
            bad += 1
            print(path)
            for p in problems:
                print('   ' + p)
    print('Схем: %d, с замечаниями: %d' % (total, bad))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
