import lzw
f=open('../files/masktype.vga', 'rb')
m=f.read()
print(lzw.is_valid_lzw_buffer(m))
b = lzw.decompress_buffer(m)
print('length:', len(b))
o=open('/tmp/look.out', 'wb')
o.write(b)
o.close()
