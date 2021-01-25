import torch
import torchvision.transforms.functional as TF

import random
import matplotlib.pyplot as plt

from sourcecode.wsi_image_utils import *
from sourcecode.logger_utils import *

from albumentations import (
    Transpose,
    RandomRotate90,
    ElasticTransform,
    GridDistortion,
    OpticalDistortion
)


def is_valid_file(filename, extensions=('.jpg', '.bmp', '.tif', '.png')):
    return str(filename).lower().endswith(extensions)


def data_augmentation(input_image, output_mask, img_input_size=(640, 640), img_output_size=(640, 640), aug=True):

    image = TF.resize(input_image, size=img_output_size)
    mask = TF.resize(output_mask, size=img_output_size) if output_mask is not None and np.any(
        np.unique(pil_to_np(output_mask) > 0)) else None

    if aug:

        # Random horizontal flipping
        if random.random() > 0.5:
            image = TF.hflip(image)
            mask = TF.hflip(mask) if mask is not None else None

        # Random vertical flipping
        if random.random() > 0.5:
            image = TF.vflip(image)
            mask = TF.vflip(mask) if mask is not None else None

        # Random rotation
        if random.random() > 0.5 and img_input_size[0] == img_input_size[1]:
            augmented = RandomRotate90(p=1)(image=np.array(image),
                                            mask=np.array(mask) if mask is not None else np.zeros(img_output_size))
            image = Image.fromarray(augmented['image'])
            mask = Image.fromarray(augmented['mask'])

        # Random transpose
        if random.random() > 0.5 and img_input_size[0] == img_input_size[1]:
            augmented = Transpose(p=1)(image=np.array(image),
                                       mask=np.array(mask) if mask is not None else np.zeros(img_output_size))
            image = Image.fromarray(augmented['image'])
            mask = Image.fromarray(augmented['mask'])

        # Random elastic transformation
        if random.random() > 0.5:
            alpha = random.randint(100, 200)
            augmented = ElasticTransform(p=1, alpha=alpha, sigma=alpha * 0.05, alpha_affine=alpha * 0.03)(
                image=np.array(image), mask=np.array(mask) if mask is not None else np.zeros(img_output_size))
            image = Image.fromarray(augmented['image'])
            mask = Image.fromarray(augmented['mask'])

        # Random GridDistortion
        if random.random() > 0.5:
            augmented = GridDistortion(p=1)(image=np.array(image),
                                            mask=np.array(mask) if mask is not None else np.zeros(img_output_size))
            image = Image.fromarray(augmented['image'])
            mask = Image.fromarray(augmented['mask'])

        # Random OpticalDistortion
        if random.random() > 0.5:
            augmented = OpticalDistortion(p=1, distort_limit=1, shift_limit=0.5)(image=np.array(image),
                                                                                 mask=np.array(
                                                                                     mask) if mask is not None else np.zeros(
                                                                                     img_output_size))
            image = Image.fromarray(augmented['image'])
            mask = Image.fromarray(augmented['mask'])

    # Transform to grayscale (1 channel)
    mask = TF.to_grayscale(mask, num_output_channels=1) if mask is not None else None

    # Transform to pytorch tensor and binarize the mask
    image = TF.to_tensor(image).float()

    unique_mask_values = np.unique(pil_to_np(mask))
    mask = torch.zeros(img_output_size) if mask is None or not np.any(unique_mask_values) else (
        torch.ones(img_output_size) if np.any(unique_mask_values) and unique_mask_values.size == 1 else TF.to_tensor(
            np_to_pil(basic_threshold(np_img=pil_to_np(mask)))).squeeze(0).float())

    return image, mask


def show_image(img):
    if isinstance(img, np.ndarray) or len(img.shape) == 2:
        plt.imshow(img, cmap='gray', vmin=0, vmax=1)
    else:
        rgb = img.permute(1, 2, 0)
        plt.imshow(rgb)


def dataset_show(dataloader, batch_size=6, show_masks=False, row_limit=10):
    cont_rows = 0
    for batch_idx, (images, masks, fname, output_size) in enumerate(dataloader):

        logger.info('Batch {}: {}/{} images {} masks {}'.format((batch_idx + 1),
                                                                (batch_idx + 1) * len(images),
                                                                len(dataloader.dataset),
                                                                images.shape,
                                                                masks.shape))
        # print('\t{}'.format(masks))

        # show 1 line of 'batch_size' images
        fig = plt.figure(figsize=(20, 20))
        for idx in np.arange(batch_size):
            ax = fig.add_subplot(1, batch_size, idx + 1, xticks=[], yticks=[])
            show_image(images[idx])
            ax.set_title("{}".format(fname[idx] if len(fname[idx]) < 15 else fname[idx][0:10] + "..."))

        if show_masks:
            # show 1 line of 'batch_size' masks
            fig = plt.figure(figsize=(20, 20))
            for idx in np.arange(batch_size):
                ax = fig.add_subplot(1, batch_size, idx + 1, xticks=[], yticks=[])
                show_image(masks[idx])

        cont_rows = cont_rows + 1
        if cont_rows >= row_limit:
            break