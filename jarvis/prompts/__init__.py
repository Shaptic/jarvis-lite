import os.path

def read_prompt(fn):
    return open(os.path.join("prompts", fn), "rt").read().strip()

orchestra = read_prompt("orchestra.txt")
weather = read_prompt("weather.txt")
todo = read_prompt("lists.txt")
