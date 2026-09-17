from app import data
import inspect
wg = data.walk_graph()
fns = [n for n in dir(data) if 'entr' in n.lower()] + [n for n in dir(wg) if 'entr' in n.lower()]
print(fns)
