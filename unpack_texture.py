#!python
import os
import sys
from PIL import Image
from xml.etree import ElementTree
import json
import plistlib


if Image is None:
    print('library <<<pillow>>> is not install. please run cmd #[ pip install pillow ] first!')
    exit(-1)

def tree_to_dict(tree):
    d = {}
    for index, item in enumerate(tree):
        if item.tag == 'key':
            if tree[index + 1].tag == 'string':
                d[item.text] = tree[index + 1].text
            elif tree[index + 1].tag == 'true':
                d[item.text] = True
            elif tree[index + 1].tag == 'false':
                d[item.text] = False
            elif tree[index + 1].tag == 'dict':
                d[item.text] = tree_to_dict(tree[index + 1])
    return d

def get_data_extension_by_format(format):
    if format == 'json':
        return '.json'
    else: return '.plist'

def get_data_filename(filename, format):
    data_filename = filename + get_data_extension_by_format(format)
    return data_filename

def frames_from_data(filename, format):
    data_filename = get_data_filename(filename, format)
    if format == 'plist':
        root = ElementTree.fromstring(open(data_filename, 'r').read())
        plist_dict = tree_to_dict(root[0])
        to_list = lambda x: x.replace('{', '').replace('}', '').split(',')
        frames = plist_dict['frames'].items()
        for k, v in frames:
            frame = v
            rectlist = to_list(frame['frame'])
            width = int(rectlist[3] if frame['rotated'] else rectlist[2])
            height = int(rectlist[2] if frame['rotated'] else rectlist[3])
            frame['box'] = (
                int(rectlist[0]),
                int(rectlist[1]),
                int(rectlist[0]) + width,
                int(rectlist[1]) + height
            )
            real_rectlist = to_list(frame['sourceSize'])
            real_width = int(real_rectlist[1] if frame['rotated'] else real_rectlist[0])
            real_height = int(real_rectlist[0] if frame['rotated'] else real_rectlist[1])
            real_sizelist = [real_width, real_height]
            frame['real_sizelist'] = real_sizelist
            offsetlist = to_list(frame['offset'])
            offset_x = int(offsetlist[1] if frame['rotated'] else offsetlist[0])
            offset_y = int(offsetlist[0] if frame['rotated'] else offsetlist[1])
            frame['result_box'] = (
                int((real_sizelist[0] - width) / 2 + offset_x),
                int((real_sizelist[1] - height) / 2 + offset_y),
                int((real_sizelist[0] + width) / 2 + offset_x),
                int((real_sizelist[1] + height) / 2 + offset_y)
            )
        return frames
    elif format == 'json':
        json_data = open(data_filename)
        data = json.load(json_data)
        frames = {}
        for f in data['frames']:
            x = int(f['frame']['x'])
            y = int(f['frame']['y'])
            w = int(f['frame']['h'] if f['rotated'] else f['frame']['w'])
            h = int(f['frame']['w'] if f['rotated'] else f['frame']['h'])
            real_w = int(f['sourceSize']['h'] if f['rotated'] else f['sourceSize']['w'])
            real_h = int(f['sourceSize']['w'] if f['rotated'] else f['sourceSize']['h'])
            d = {
                'box': (
                    x,
                    y,
                    x + w,
                    y + h
                ),
                'real_sizelist': [
                    real_w,
                    real_h
                ],
                'result_box': (
                    int((real_w - w) / 2),
                    int((real_h - h) / 2),
                    int((real_w + w) / 2),
                    int((real_h + h) / 2)
                ),
                'rotated': f['rotated']
            }
            frames[f['filename']] = d
        json_data.close()
        return frames.items()
    elif format == 'cocos':
        pl = plistlib.readPlist(data_filename)
        data = pl['frames'].items()
        frames = {}
        for k, f in data:
            x = int(f['x'])
            y = int(f['y'])
            w = int(f['width'])
            h = int(f['height'])
            real_w = int(f['originalWidth'])
            real_h = int(f['originalHeight'])
            d = {
                'box': (
                    x,
                    y,
                    x + w,
                    y + h
                ),
                'real_sizelist': [
                    real_w,
                    real_h
                ],
                'result_box': (
                    int((real_w - w) / 2),
                    int((real_h - h) / 2),
                    int((real_w + w) / 2),
                    int((real_h + h) / 2)
                ),
                'rotated': False
            }
            frames[k] = d
        return frames.items()
    else:
        print('Wrong data format on parsing: '' + format + ''!')
        exit(1)


def gen_png_from_data(filename, format):
    big_image = Image.open(filename + '.png')
    frames = frames_from_data(filename, format)
    for k, v in frames:
        frame = v
        box = frame['box']
        outfile = (filename + '/' + k).replace('gift_', '')
        rect_on_big = big_image.crop(box)
        real_sizelist = frame['real_sizelist']
        # make folder and get output file name
        dirname = os.path.dirname(outfile)
        if not os.path.isdir(dirname):
            os.makedirs(dirname)

        # if frame['rotated']:
        #     rect_on_big = rect_on_big.rotate(angle=90, expand=1)
        # rect_on_big.save(outfile)

        result_image = Image.new('RGBA', real_sizelist, (0, 0, 0, 0))
        result_box = frame['result_box']
        result_image.paste(rect_on_big, result_box, mask=0)
        if frame['rotated']:
            result_image = result_image.rotate(angle=90, expand=1)
        result_image.save(outfile)
        print(outfile, "generated")

def find_all_file_with_extensions(filepath, ext):
    #遍历filepath下所有文件，包括子目录
    files = os.listdir(filepath)
    ret = []
    for fi in files:
        fi_d = os.path.join(filepath,fi)
        if os.path.isdir(fi_d):
            tmp = find_all_file_with_extensions(fi_d, ext)
            for v in tmp:
                ret.append(v)
        else:
            file_ext = os.path.splitext(fi_d)
            if file_ext[1] == ext:
                ret.append(fi_d)
            else:
                print('skip file [' + fi_d + ']');
    return ret

def unpack_file(filename, format = 'plist'):
    if format == 'plist':
        print('.plist data format passed')
    elif format == 'json':
        print('.json data format passed')
    elif format == 'cocos':
        print('.cocos data format passed')
    else:
        print('Wrong data format passed '' + format + ''!')
        exit(1)

    data_filename = get_data_filename(filename, format)
    png_filename = filename + '.png'
    if os.path.exists(data_filename) and os.path.exists(png_filename):
        gen_png_from_data(filename, format)
    else:
        print('Make sure you have both ' + data_filename + ' and ' + png_filename + ' files in the same directory')

def print_usage():
    print(sys.argv[0] + '<file name without extension or folder path> <format (plist|cocos|json)>')

if __name__ == '__main__':
    if sys.argv.__len__() <= 2:
        print_usage()
        exit(-1)
    if os.path.isdir(sys.argv[1]):
        filelst = find_all_file_with_extensions(sys.argv[1], get_data_extension_by_format(sys.argv[2]))
        for file in filelst:
            unpack_file(os.path.splitext(file)[0], sys.argv[2])
    else:
        unpack_file(sys.argv[1], sys.argv[2])
