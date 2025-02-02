# filter warnings
import warnings
warnings.simplefilter(action="ignore", category=FutureWarning)
import os
import tensorflow as tf
import logging

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

logger = tf.get_logger()
logger.setLevel(logging.ERROR)

# keras imports
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.models import Model, load_model
from tensorflow.keras.layers import Dense, GlobalAveragePooling2D, Input
from tensorflow.keras.utils import to_categorical
from tensorflow.keras.optimizers import SGD
from tensorflow.keras.callbacks import ModelCheckpoint

# other imports
import json
import datetime
import time

from utils import generate_dataset, generate_batches, generate_batches_with_augmentation, create_folders

# load the user configs
with open('conf.json') as f:    
  config = json.load(f)

# config variables
weights     = config["weights"]
train_path    = config["train_path"]
test_path     = config["test_path"]
model_path    = config["model_path"]
batch_size    = config["batch_size"]
epochs        = config["epochs"]
classes       = config["classes"]
augmented_data     = config["augmented_data"]
validation_split   = config["validation_split"]
data_augmentation  = config["data_augmentation"]
epochs_after_unfreeze = config["epochs_after_unfreeze"]
checkpoint_period = config["checkpoint_period"]
checkpoint_period_after_unfreeze = config["checkpoint_period_after_unfreeze"]

create_folders(model_path, augmented_data)

# create model
if weights=="imagenet":
  base_model = MobileNetV2(include_top=False, weights=weights, 
                            input_tensor=Input(shape=(224,224,3)), input_shape=(224,224,3))
  top_layers = base_model.output
  top_layers = GlobalAveragePooling2D()(top_layers)
  top_layers = Dense(1024, activation='relu')(top_layers)
  predictions = Dense(classes, activation='softmax')(top_layers)
  model = Model(inputs=base_model.input, outputs=predictions)
elif weights=="":
  base_model = MobileNetV2(include_top=False,
                            input_tensor=Input(shape=(224,224,3)), input_shape=(224,224,3))
  top_layers = base_model.output
  top_layers = GlobalAveragePooling2D()(top_layers)
  top_layers = Dense(1024, activation='relu')(top_layers)
  predictions = Dense(classes, activation='softmax')(top_layers)
  model = Model(inputs=base_model.input, outputs=predictions)
else:
  model = load_model(weights)
print ("[INFO] successfully loaded base model and model...")

# create callbacks
checkpoint = ModelCheckpoint("logs/weights.h5", monitor='loss', save_best_only=True, period=checkpoint_period)

# start time
start = time.time()

print ("Freezing the base layers. Unfreeze the top 2 layers...")
for layer in model.layers[:-3]:
    layer.trainable = False
model.compile(optimizer='rmsprop', loss='categorical_crossentropy')

print ("Start training...")
import glob
files = []
for ext in [ 'png', 'jpg', 'jpeg' ]:
  files.extend(glob.glob(train_path + '/*/*' + ext))
samples = len(files)
x, y = generate_dataset(files, classes)
print("dataset # of x:%u, #of y:%u" % (len(x), len(y)))

if data_augmentation:
  model.fit(generate_batches_with_augmentation(train_path, batch_size, validation_split, augmented_data), 
            verbose=1, epochs=epochs, callbacks=[checkpoint])
else:
  # model.fit(generate_batches(files, classes, batch_size), epochs=epochs, 
  #           steps_per_epoch=samples//batch_size,
  #           verbose=1,
  #           callbacks=[checkpoint])
  model.fit(x, y, batch_size=batch_size, epochs=epochs, validation_split=validation_split, verbose=1, callbacks=[checkpoint])

print ("Saving...")
model.save(model_path + "/save_model_stage1.h5") 

# print ("Visualization...")
# for i, layer in enumerate(base_model.layers):
#    print(i, layer.name)

if epochs_after_unfreeze > 0:
  print ("Unfreezing all layers...")
  for i in range(len(model.layers)):
    model.layers[i].trainable = True
  model.compile(optimizer=SGD(lr=0.0001, momentum=0.9), loss='categorical_crossentropy')

  print ("Start training - phase 2...")
  checkpoint = ModelCheckpoint("logs/weights.h5", monitor='loss', save_best_only=True, period=checkpoint_period_after_unfreeze)
  if data_augmentation:
    model.fit(generate_batches_with_augmentation(train_path, batch_size, validation_split, augmented_data), 
              verbose=1, epochs=epochs_after_unfreeze, callbacks=[checkpoint])
  else:
    model.fit(x, y, batch_size=batch_size, epochs=epochs_after_unfreeze, validation_split=validation_split, verbose=1, callbacks=[checkpoint])
    # model.fit(generate_batches(files, classes, batch_size), epochs=epochs_after_unfreeze, 
    #           steps_per_epoch=samples//batch_size, verbose=1, callbacks=[checkpoint])

  print ("Saving...")
  model.save(model_path + "/save_model_stage2.h5") 

# end time
end = time.time()
print ("[STATUS] end time - {}".format(datetime.datetime.now().strftime("%Y-%m-%d %H:%M")))
print ("[STATUS] total duration: {}".format(end - start))
