import base64
import os
import time
import uuid
from io import BytesIO
import numpy as np


def img_to_base64(image_file):
    # assert image_file.lower().endswith('jpg') or image_file.lower().endswith('jpeg')
    from PIL import Image

    EXTENSIONS = {'.png': 'PNG', '.apng': 'PNG', '.blp': 'BLP', '.bmp': 'BMP', '.dib': 'DIB', '.bufr': 'BUFR',
                  '.cur': 'CUR', '.pcx': 'PCX', '.dcx': 'DCX', '.dds': 'DDS', '.ps': 'EPS', '.eps': 'EPS',
                  '.fit': 'FITS', '.fits': 'FITS', '.fli': 'FLI', '.flc': 'FLI', '.fpx': 'FPX', '.ftc': 'FTEX',
                  '.ftu': 'FTEX', '.gbr': 'GBR', '.gif': 'GIF', '.grib': 'GRIB', '.h5': 'HDF5', '.hdf': 'HDF5',
                  '.jp2': 'JPEG2000', '.j2k': 'JPEG2000', '.jpc': 'JPEG2000', '.jpf': 'JPEG2000', '.jpx': 'JPEG2000',
                  '.j2c': 'JPEG2000', '.icns': 'ICNS', '.ico': 'ICO', '.im': 'IM', '.iim': 'IPTC', '.jfif': 'JPEG',
                  '.jpe': 'JPEG', '.jpg': 'JPEG', '.jpeg': 'JPEG', '.tif': 'TIFF', '.tiff': 'TIFF', '.mic': 'MIC',
                  '.mpg': 'MPEG', '.mpeg': 'MPEG', '.mpo': 'MPO', '.msp': 'MSP', '.palm': 'PALM', '.pcd': 'PCD',
                  '.pdf': 'PDF', '.pxr': 'PIXAR', '.pbm': 'PPM', '.pgm': 'PPM', '.ppm': 'PPM', '.pnm': 'PPM',
                  '.psd': 'PSD', '.qoi': 'QOI', '.bw': 'SGI', '.rgb': 'SGI', '.rgba': 'SGI', '.sgi': 'SGI',
                  '.ras': 'SUN', '.tga': 'TGA', '.icb': 'TGA', '.vda': 'TGA', '.vst': 'TGA', '.webp': 'WEBP',
                  '.wmf': 'WMF', '.emf': 'WMF', '.xbm': 'XBM', '.xpm': 'XPM'}

    from pathlib import Path
    ext = Path(image_file).suffix
    if ext in EXTENSIONS:
        iformat = EXTENSIONS[ext]
    else:
        raise ValueError("Invalid file extension %s for file %s" % (ext, image_file))

    image = Image.open(image_file)
    buffered = BytesIO()
    image.save(buffered, format=iformat)
    img_str = base64.b64encode(buffered.getvalue())
    # FIXME: unsure about below
    img_str = str(bytes("data:image/%s;base64," % iformat.lower(), encoding='utf-8') + img_str)

    return img_str


def base64_to_img(img_str, output_path):
    # Split the string on "," to separate the metadata from the base64 data
    meta, base64_data = img_str.split(",", 1)
    # Extract the format from the metadata
    img_format = meta.split(';')[0].split('/')[-1]
    # Decode the base64 string to bytes
    img_bytes = base64.b64decode(base64_data)
    # Create output file path with the correct format extension
    output_file = f"{output_path}.{img_format}"
    # Write the bytes to a file
    with open(output_file, "wb") as f:
        f.write(img_bytes)
    print(f"Image saved to {output_file} with format {img_format}")
    return output_file


def llava_prep(file, llava_model,
               prompt=None,
               chat_conversation=[],
               allow_prompt_auto=True,
               image_model='llava-v1.6-vicuna-13b', temperature=0.2,
               top_p=0.7, max_new_tokens=512,
               client=None):
    if prompt in ['auto', None] and allow_prompt_auto:
        prompt = "Describe the image and what does the image say?"
        # prompt = "According to the image, describe the image in full details with a well-structured response."
        if file in ['', None]:
            # let model handle if no prompt and no file
            prompt = ''
    # allow prompt = '', will describe image by default

    prefix = ''
    if llava_model.startswith('http://'):
        prefix = 'http://'
    if llava_model.startswith('https://'):
        prefix = 'https://'
    llava_model = llava_model[len(prefix):]

    llava_model_split = llava_model.split(':')
    assert len(llava_model_split) >= 2
    # FIXME: Allow choose model in UI
    if len(llava_model_split) >= 2:
        pass
        # assume default model is ok
        # llava_ip = llava_model_split[0]
        # llava_port = llava_model_split[1]
    if len(llava_model_split) >= 3:
        image_model = llava_model_split[2]
        llava_model = ':'.join(llava_model_split[:2])
    # add back prefix
    llava_model = prefix + llava_model

    if client is None:
        from gradio_client import Client
        if False:
            client = Client(llava_model, serialize=False)
        else:
            client = Client(llava_model)
    load_res = client.predict(api_name='/demo_load')
    model_options = [x[1] for x in load_res['choices']]
    assert len(model_options), "LLaVa endpoint has no models: %s" % str(load_res)

    # if no default choice or default choice not there, choose first
    if not image_model or image_model not in model_options:
        image_model = model_options[0]

    # test_file_local, test_file_server = client.predict(file_to_upload, api_name='/upload_api')

    image_process_mode = "Default"
    include_image = False
    if isinstance(file, np.ndarray):
        from PIL import Image
        im = Image.fromarray(file)
        file = "%s.jpeg" % str(uuid.uuid4())
        im.save(file)

    if False:
        if file and os.path.isfile(file):
            img_str = img_to_base64(file)
        else:
            img_str = None
        res1 = client.predict(prompt, chat_conversation, img_str, image_process_mode, include_image, api_name='/textbox_api_btn')
    else:
        res1 = client.predict(prompt, chat_conversation, file, image_process_mode, include_image, api_name='/textbox_api_btn')  # FIXME: Gradio 4 issue, can't send string as image bytes

    model_selector, temperature, top_p, max_output_tokens = image_model, temperature, top_p, max_new_tokens

    return model_selector, max_output_tokens, include_image, client, image_model


def get_llava_response(file=None,
                       llava_model=None,
                       prompt=None,
                       chat_conversation=[],
                       allow_prompt_auto=False,
                       image_model='llava-v1.6-vicuna-13b', temperature=0.2,
                       top_p=0.7, max_new_tokens=512,
                       client=None,
                       ):
    model_selector, max_output_tokens, include_image, client, image_model = \
        llava_prep(file, llava_model,
                   prompt=prompt,
                   chat_conversation=chat_conversation,
                   allow_prompt_auto=allow_prompt_auto,
                   image_model=image_model,
                   temperature=temperature,
                   top_p=top_p,
                   max_new_tokens=max_new_tokens,
                   client=client)

    res = client.predict(model_selector, temperature, top_p, max_output_tokens, include_image,
                         api_name='/textbox_api_submit')
    res = res[-1][-1]
    return res, prompt


def get_llava_stream(file, llava_model,
                     prompt=None,
                     chat_conversation=[],
                     allow_prompt_auto=False,
                     image_model='llava-v1.6-vicuna-13b', temperature=0.2,
                     top_p=0.7, max_new_tokens=512,
                     client=None,
                     ):
    image_model = os.path.basename(image_model)  # in case passed HF link
    model_selector, max_output_tokens, include_image, client, image_model = \
        llava_prep(file, llava_model,
                   prompt=prompt,
                   chat_conversation=chat_conversation,
                   allow_prompt_auto=allow_prompt_auto,
                   image_model=image_model,
                   temperature=temperature,
                   top_p=top_p,
                   max_new_tokens=max_new_tokens,
                   client=client)

    verbose_level = 0

    if verbose_level == 2:
        print("Get job", flush=True)

    job = client.submit(model_selector, temperature, top_p, max_output_tokens, include_image,
                        api_name='/textbox_api_submit')
    if verbose_level == 2:
        print("Got job", flush=True)

    job_outputs_num = 0
    while not job.done():
        outputs_list = job.outputs().copy()
        job_outputs_num_new = len(outputs_list[job_outputs_num:])
        for num in range(job_outputs_num_new):
            res = outputs_list[job_outputs_num + num]
            if verbose_level == 2:
                print('Stream %d: %s' % (num, res), flush=True)
            elif verbose_level == 1:
                print('Stream %d' % (job_outputs_num + num), flush=True)
            if res and len(res[0]) > 0:
                yield res[-1][-1]
        job_outputs_num += job_outputs_num_new
        time.sleep(0.01)

    outputs_list = job.outputs().copy()
    job_outputs_num_new = len(outputs_list[job_outputs_num:])
    for num in range(job_outputs_num_new):
        res = outputs_list[job_outputs_num + num]
        if verbose_level == 2:
            print('Final Stream %d: %s' % (num, res), flush=True)
        elif verbose_level == 1:
            print('Final Stream %d' % (job_outputs_num + num), flush=True)
        if res and len(res[0]) > 0:
            yield res[-1][-1]
    job_outputs_num += job_outputs_num_new
    if verbose_level == 1:
        print("total job_outputs_num=%d" % job_outputs_num, flush=True)
