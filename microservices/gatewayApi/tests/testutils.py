
def trimleft (lines, chars):
    output = ""
    for line in lines.split("\n"):
        output = output + line[chars:] + "\n"
    return output