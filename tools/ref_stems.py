import sys
from PIL import Image, ImageDraw, ImageFont
path = sys.argv[1]
SIZE = 2000  # px per em -> 1 unit = 2px
def runs(line):
    out=[];start=None
    for i,v in enumerate(line):
        if v and start is None: start=i
        if not v and start is not None: out.append((start,i)); start=None
    if start is not None: out.append((start,len(line)))
    return out
font = ImageFont.truetype(path, SIZE)
def render(ch):
    W=H=SIZE*2
    im = Image.new("L",(W,H),0)
    d = ImageDraw.Draw(im)
    d.text((SIZE//2, SIZE), ch, font=font, fill=255, anchor="ls")  # baseline at y=SIZE
    return im.point(lambda v:255 if v>127 else 0)
def u(px): return round(px*1000/SIZE)
def hscan(im, yunits):
    y = SIZE - int(yunits*SIZE/1000)
    row = im.crop((0,y,im.width,y+1)).getdata()
    return [(u(a-SIZE//2),u(b-SIZE//2)) for a,b in runs(list(row))]
def vscan(im, xunits):
    x = SIZE//2 + int(xunits*SIZE/1000)
    col = im.crop((x,0,x+1,im.height)).getdata()
    return [(u(SIZE-b),u(SIZE-a)) for a,b in runs(list(col))]
for ch,ys,xs in [("H",[100,360,650,10,710],[273,100,400]),("n",[250,100,480,5,505],[240,100,380]),("o",[250,258],[198,200]),("O",[360],[270]),("d",[250,700],[100]),("a",[250,400],[200]),("e",[250,300],[170]),("p",[250],[200]),("g",[250,300],[200])]:
    im = render(ch)
    print("---",ch)
    for y in ys: print(" y=%d horizontal runs:"%y, hscan(im,y))
    for x in xs: print(" x=%d vertical runs:"%x, vscan(im,x))
