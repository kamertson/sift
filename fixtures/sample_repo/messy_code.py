"""Intentionally messy code used as a low-quality fixture."""

def doStuff(x,y,z=None):
  a=0
  if x:
   for i in range(10):
    if y:
     if z:
      a+=i*y*z
     else:
      a+=i*y
    else:
     a+=i
   if a>100:
    if a>200:
     if a>300:
      return a
     return a-1
    return a-2
  else:
   return -1
  return a

def weird_function( data ):
    result=[]
    for item in data:
        if item==None: continue
        if type(item)==str:
            if len(item)>0:
                if item[0].isupper():
                    result.append(item.lower())
                else:
                    result.append(item.upper())
            else:
                result.append("")
        elif type(item)==int:
            if item%2==0:
                result.append(item*2)
            else:
                if item<0:
                    result.append(0)
                else:
                    result.append(item)
        else:
            result.append(None)
    return result
