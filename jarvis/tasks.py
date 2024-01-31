import abc


class Task(abc.ABC):
    def prepare(self, task_details):
        validate(task_details, *self.SCHEMA)
        self.task = task_details

    def execute(self):
        raise NotImplemented

def validate(task, fields, types):
    assert len(fields) == len(types)
    for i, field in enumerate(fields):
        value = task.get(field, None)
        optional = field.endswith('?')

        if value is None:
            if not optional:
                raise TypeError(f"field '{field}' not in {task}")
            continue

        if types[i] != 'any' and not isinstance(value, types[i]):
            raise TypeError(f"field '{field}' is not of type(s) {types[i]}: {task}")
