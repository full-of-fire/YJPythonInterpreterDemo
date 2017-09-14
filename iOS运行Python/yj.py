
	
		
def add(a,b):
    print "in python function add"
    print "a = " + str(a)
    print "b = " + str(b)
    print "ret = " + str(a+b)
    return

def foo(a):
    
    print "in python function foo"
    print "a = " + str(a)
    print "ret = " + str(a * a)
    return

class guestlist:
    def __init__(self):
        print "aaaa"
    def p():
        print "bbbbb"
    def __getitem__(self, id):
        return "ccccc"
def update():
    guest = guestlist()
    print guest['aa']
