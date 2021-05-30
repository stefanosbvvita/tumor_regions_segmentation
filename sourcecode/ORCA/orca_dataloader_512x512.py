from sourcecode.ORCA.orca_dataloader import ORCADataset
from sourcecode.dataloader_utils import *

from torch.utils.data import Dataset
from sklearn.model_selection import train_test_split

import os.path


class ORCADataset512x512(ORCADataset):

    def __init__(self,
                 img_dir="../../datasets/ORCA_512x512",
                 dataset_type="training",
                 augmentation=None,
                 augmentation_strategy="random",
                 color_model="LAB",
                 start_epoch=1):
        self.img_dir = img_dir
        self.dataset_type = dataset_type
        self.augmentation = augmentation
        self.augmentation_strategy = augmentation_strategy
        self.color_model = color_model
        self.samples = load_dataset(img_dir, dataset_type)
        self.used_images = set()
        self.epoch = start_epoch

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        path_img, path_mask, fname = self.samples[idx]
        image = load_pil_image(path_img, False, self.color_model)
        mask = load_pil_image(path_mask) if is_valid_file(path_mask) else None

        x, y, fname, original_size = self.transform(image, mask, fname)
        return [x, y if mask is not None else path_mask, fname, original_size]

    def transform(self, image, mask, fname):
        #should_augment = False
        #should_augment = (self.augmentation and fname in self.used_images)

        if fname in self.used_images:
            self.epoch += 1
            self.used_images.clear()
        self.used_images.add(fname)

        augmentation_operations = []
        if self.augmentation_strategy == "no_augmentation" \
                or (self.augmentation_strategy == 'random' and self.epoch == 1):

            augmentation_operations = None

        elif self.augmentation_strategy == 'random':

            augmentation_operations = self.augmentation.copy()
            augmentation_operations.remove(None)

        elif self.augmentation_strategy == 'one_by_epoch':

            idx = (self.epoch-1) % len(self.augmentation)
            augmentation_operations.append(self.augmentation[idx])

        if len(self.used_images) <= 1:
            logger.info("Epoch: '{}' augmentation {} {}".format(self.epoch, self.augmentation_strategy,
                                                                augmentation_operations))

        #x, y = data_augmentation(image, mask, self.img_input_size, self.img_output_size, should_augment)
        #x, y = data_augmentation(image, mask, self.img_input_size, self.img_output_size, False)
        x, y, used_augmentations = data_augmentation(image, mask, (512, 512), (512, 512), augmentation_operations)
        return x, y, fname, image.size


def load_dataset(img_dir, dataset_type):

    images = []
    classes = ["tumor"]
    dataset_root_dir = "{}/{}".format(img_dir, dataset_type)
    logger.info("[{}] {}".format(dataset_type, dataset_root_dir))

    for root, d, _ in sorted(os.walk(dataset_root_dir)):

        for cls in sorted([cls for cls in d if cls in classes]):

            original_dir = "{}/{}/tma".format(dataset_root_dir, cls)
            mask_dir = "{}/lesion_annotations".format(dataset_root_dir)

            for dirpath, dirnames, filenames in sorted(os.walk(original_dir)):
                for fname in sorted(filenames):

                    path_img = os.path.join(original_dir, fname)
                    path_mask = os.path.join(mask_dir, fname.replace(".png", "_mask.png"))

                    #if is_valid_file(path_img) and first_train.find(fname) < 0:
                    if is_valid_file(path_img):
                        item = (path_img, path_mask, fname)
                        images.append(item)
    #first_train = ""
    return images


def create_dataloader(batch_size=1,
                      shuffle=False,
                      dataset_dir="../../datasets/ORCA",
                      color_model="LAB",
                      augmentation=None,
                      augmentation_strategy="random",
                      start_epoch=1,
                      validation_split=0.0):

    if augmentation is None:
        augmentation = [None, "horizontal_flip", "vertical_flip", "rotation", "transpose", "elastic_transformation",
                        "grid_distortion", "optical_distortion"]

    image_datasets = {x: ORCADataset512x512(img_dir=dataset_dir,
                                             dataset_type='testing' if x == 'test' else 'training',
                                             augmentation=augmentation,
                                             augmentation_strategy='no_augmentation' if x != 'train' else augmentation_strategy,
                                             color_model=color_model,
                                             start_epoch=start_epoch) for x in ['train', 'valid', 'test']}

    if validation_split > 0:

        train_dataset_index, valid_dataset_index = train_test_split(range(len(image_datasets['train'])),
                                                                    test_size=validation_split, random_state=0)
        train_dataset_index.sort()
        valid_dataset_index.sort()

        train_dataset_samples = [image_datasets['train'].samples[index] for index in train_dataset_index]
        valid_dataset_samples = [image_datasets['train'].samples[index] for index in valid_dataset_index]

        image_datasets['train'].samples = train_dataset_samples
        image_datasets['valid'].samples = valid_dataset_samples

    dataloaders = {
        x: torch.utils.data.DataLoader(image_datasets[x], batch_size=batch_size, shuffle=shuffle, num_workers=0) for x
        in ['train', 'valid', 'test']}

    dataset_sizes = {x: len(image_datasets[x]) for x in ['train', 'valid', 'test']}

    if validation_split <= 0:
        del image_datasets['valid']
        del dataloaders['valid']
        del dataset_sizes['valid']

    logger.info("Train images: {} augmentation: {}".format(dataset_sizes['train'], augmentation_strategy))
    if validation_split > 0:
        logger.info("Valid images: {} augmentation: {}".format(dataset_sizes['valid'], 'no_augmentation'))
    logger.info("Test images: {} augmentation: {}".format(dataset_sizes['test'], 'no_augmentation'))

    return dataloaders
