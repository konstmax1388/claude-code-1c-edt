# -*- coding: utf-8 -*-
"""Проверка ролей EDT-проекта перед загрузкой конфигурации в базу.

Что ищет:
  1. Нарушение порядка блоков <object> в Rights.rights. EDT пишет их по возрастанию UUID объекта,
     конфигуратор при загрузке на этот порядок полагается. Блок, дописанный в конец файла,
     вешает загрузку без ошибки и без записи в лог.
  2. Права на перечисления (Enum.*). В типовых ролях их нет, у нас они давали то же зависание.
  3. Права на HTTP-сервис целиком (HTTPService.X без URLTemplate). Платформа такие права молча выбрасывает.

Запуск:
  python check_rights_order.py <путь к src EDT-проекта> [Роль1 Роль2 ...]

Без списка ролей проверяются все. Код возврата 1, если что-то найдено.
"""
import io
import os
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

FOLDER = {
    'Catalog': 'Catalogs', 'Document': 'Documents', 'Enum': 'Enums', 'DataProcessor': 'DataProcessors',
    'Report': 'Reports', 'InformationRegister': 'InformationRegisters',
    'AccumulationRegister': 'AccumulationRegisters', 'AccountingRegister': 'AccountingRegisters',
    'CalculationRegister': 'CalculationRegisters', 'HTTPService': 'HTTPServices', 'WebService': 'WebServices',
    'ExchangePlan': 'ExchangePlans', 'Constant': 'Constants', 'CommonForm': 'CommonForms',
    'CommonCommand': 'CommonCommands', 'ScheduledJob': 'ScheduledJobs', 'DocumentJournal': 'DocumentJournals',
    'CommonModule': 'CommonModules', 'ChartOfCharacteristicTypes': 'ChartsOfCharacteristicTypes',
    'ChartOfAccounts': 'ChartsOfAccounts', 'ChartOfCalculationTypes': 'ChartsOfCalculationTypes',
    'BusinessProcess': 'BusinessProcesses', 'Task': 'Tasks', 'CommonAttribute': 'CommonAttributes',
    'SessionParameter': 'SessionParameters', 'FilterCriterion': 'FilterCriteria',
}
KIND_TAG = {
    'TabularSection': 'tabularSections', 'Attribute': 'attributes', 'Command': 'commands', 'Form': 'forms',
    'Dimension': 'dimensions', 'Resource': 'resources', 'Template': 'templates', 'Column': 'columns',
    'URLTemplate': 'urlTemplates', 'Method': 'methods', 'Operation': 'operations',
    'AccountingFlag': 'accountingFlags', 'ExtDimensionAccountingFlag': 'extDimensionAccountingFlags',
    'AddressingAttribute': 'addressingAttributes',
}


class Project:
    def __init__(self, src):
        self.src = src
        self.cache = {}

    def mdo_path(self, fqn):
        if fqn.startswith('Subsystem.'):
            names = fqn.split('.')[1::2]
            path = os.path.join(self.src, 'Subsystems', names[0])
            for name in names[1:]:
                path = os.path.join(path, 'Subsystems', name)
            return os.path.join(path, names[-1] + '.mdo')
        kind, name = fqn.split('.')[:2]
        return os.path.join(self.src, FOLDER[kind], name, name + '.mdo')

    def uuid(self, fqn):
        """UUID объекта или его члена. Стандартный реквизит идет сразу за владельцем, ключ у него владельца."""
        if fqn in self.cache:
            return self.cache[fqn]
        if '.StandardAttribute.' in fqn:
            value = self.uuid(fqn.split('.StandardAttribute.')[0])
        elif fqn.startswith('Subsystem.'):
            value = self._first_uuid(self.mdo_path(fqn))
        else:
            segs = fqn.split('.')
            text = open(self.mdo_path(fqn), encoding='utf-8').read()
            if len(segs) == 2:
                value = self._first_uuid_text(text)
            else:
                rest = segs[2:]
                # реквизит шапки не искать среди реквизитов табличных частей
                scope = text if rest[0] == 'TabularSection' else re.sub(
                    r'<tabularSections uuid=.*?</tabularSections>', '', text, flags=re.S)
                value = None
                for kind, name in zip(rest[0::2], rest[1::2]):
                    tag = KIND_TAG[kind]
                    m = re.search(r'<%s uuid="([0-9a-f-]{36})">(?:(?!<name>).)*?<name>%s</name>'
                                  % (tag, re.escape(name)), scope, re.S)
                    if not m:
                        raise KeyError(fqn)
                    value = m.group(1)
                    scope = scope[m.start():scope.find('</%s>' % tag, m.end())]
        self.cache[fqn] = value
        return value

    @staticmethod
    def _first_uuid_text(text):
        return re.search(r'uuid="([0-9a-f-]{36})"', text).group(1)

    def _first_uuid(self, path):
        return self._first_uuid_text(open(path, encoding='utf-8').read())


def check_role(project, role):
    path = os.path.join(project.src, 'Roles', role, 'Rights.rights')
    text = open(path, encoding='utf-8').read().replace('\r\n', '\n')
    names = re.findall(r'\t<object>\n\t\t<name>([^<]+)</name>', text)
    problems = []

    previous = None
    for name in names:
        if name.startswith('Enum.'):
            problems.append('права на перечисление: %s' % name)
        if name.startswith('HTTPService.') and '.URLTemplate.' not in name:
            problems.append('право на HTTP-сервис целиком (нужно на метод): %s' % name)
        try:
            key = project.uuid(name)
        except (KeyError, FileNotFoundError, AttributeError):
            continue  # объект вида, который скрипт не разбирает: не ориентир
        if previous and key < previous[1]:
            problems.append('порядок нарушен: %s стоит после %s' % (name, previous[0]))
        previous = (name, key)
    return len(names), problems


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    project = Project(sys.argv[1])
    roles_dir = os.path.join(project.src, 'Roles')
    roles = sys.argv[2:] or sorted(os.listdir(roles_dir))
    bad = 0
    for role in roles:
        if not os.path.exists(os.path.join(roles_dir, role, 'Rights.rights')):
            continue
        count, problems = check_role(project, role)
        if problems:
            bad += 1
            print('%s (%d объектов)' % (role, count))
            for p in problems:
                print('   ' + p)
    print('Проверено ролей: %d, с замечаниями: %d' % (len(roles), bad))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
