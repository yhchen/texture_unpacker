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


def frames_from_data(filename, format):
    if format == 'plist':
        data_filename = filename + '.plist'
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
        data_filename = filename + '.json'
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
        data_filename = filename + '.plist'
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

def find_all_file_with_extensions(filepath, ext, handler):
    #遍历filepath下所有文件，包括子目录
    files = os.listdir(filepath)
    for fi in files:
        fi_d = os.path.join(filepath,fi)            
        if os.path.isdir(fi_d):
            find_all_file_with_extensions(fi_d, ext, handler)                  
        else:
            file_ext = os.path.splitext(fi_d)
            if file_ext[1] == ext:
                try:
                    print('handle file:[' + fi_d + ']')
                    handler(file_ext[0])
                except Exception as ex:
                    print('got exception:[');
                    print(ex.__str__()+']')
            else:
                print('skip file [' + fi_d + ']');

def unpack_file(filename, format):
    format = 'plist'
    ext = '.plist'
    if format == 'plist':
        print('.plist data format passed')
    elif format == 'json':
        ext = '.json'
        print('.json data format passed')
    elif format == 'cocos':
        print('.cocos data format passed')
    else:
        print('Wrong data format passed '' + format + ''!')
        exit(1)

    data_filename = filename + ext
    png_filename = filename + '.png'
    if os.path.exists(data_filename) and os.path.exists(png_filename):
        gen_png_from_data(filename, format)
    else:
        print('Make sure you have both ' + data_filename + ' and ' + png_filename + ' files in the same directory')

def unpack_cocos_file(filename):
    unpack_file(filename, 'cocos')

def unpack_plist_file(filename):
    unpack_file(filename, 'plist')

if __name__ == '__main__':
    if sys.argv.__len__() >= 1:
        find_all_file_with_extensions('./', '.plist', unpack_plist_file)
    else:
        filename = sys.argv[1]
        unpack_plist_file(filename)
