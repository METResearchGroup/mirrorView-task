
# used to generate list for preload.js

import os
import json

image_dirs = [
    'img/stim_set_bridge', 
    'img/stim_set_control_dist_100', 
    'img/stim_set_control_pol_600',
    'img/stim_set_top_100_dwell_dem',
    'img/stim_set_top_100_dwell_rep',
    'img/stim_set_top_100_like_share_dem',
    'img/stim_set_top_100_like_share_dem',
]

all_images = []

for dir_path in image_dirs:
    image_files = [os.path.join(dir_path, f) for f in os.listdir(f'public/{dir_path}') if os.path.isfile(os.path.join(f'public/{dir_path}', f))]
    all_images.extend(image_files)

js_code = f"""
var preload_images = {json.dumps(all_images, indent=2)};
"""

with open('public/preload.js', 'w') as f:
    f.write(js_code)

print("preload.js has been generated in the public folder.")