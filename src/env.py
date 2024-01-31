import os

ENV = {
    'openai': os.environ.pop('OPENAI_KEY').strip(),
    'data': os.environ.pop('JARVIS_DATA',
        os.path.abspath(os.path.join(os.getcwd(), '..', 'data'))
    )
}
