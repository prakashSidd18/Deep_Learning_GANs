import numpy as np
import keras
from keras.models import Sequential
from keras.layers.core import Dense, Dropout, Flatten, Reshape
from keras.layers.convolutional import Conv2D, MaxPooling2D, UpSampling2D
from keras.layers.normalization import BatchNormalization
from keras.optimizers import SGD, Adagrad, RMSprop
from keras.datasets import mnist
from PIL import Image
import matplotlib as plt
import argparse
import math


def generator_model():
	model = Sequential()
	model.add(Dense(1024, input_shape=(100,), activation='tanh'))
	model.add(Dense(128*7*7))
	model.add(BatchNormalization())
	model.add(Reshape((7,7,128), input_shape=(128*7*7,)))
	model.add(UpSampling2D(size=(2,2)))
	model.add(Conv2D(64, (5,5), border_mode='same', activation='tanh'))
	model.add(UpSampling2D(size=(2,2)))
	model.add(Conv2D(1, (5,5), border_mode='same', activation='tanh'))
    #print model.summary
	return model

def discriminator_model():
	model = Sequential()
	model.add(Conv2D(64, (5,5), border_mode='same', input_shape=(28,28,1), activation='tanh'))
	model.add(MaxPooling2D(pool_size=(2,2)))
	model.add(Conv2D(128, (5,5), activation='tanh'))
	model.add(MaxPooling2D(pool_size=(2,2)))
	model.add(Flatten())
	model.add(Dense(1024, activation='tanh'))
	model.add(Dense(1, activation='sigmoid'))
    #print model.summary
	return model

def generator_containing_discriminator(generator, discriminator):
	model = Sequential()
	model.add(generator)
	discriminator.trainable = False
	model.add(discriminator)
	return model

def combine_images(generated_images):
    num = generated_images.shape[0]
    width = int(math.sqrt(num))
    #print width
    height = int(math.ceil(float(num)/width))
    #print width
    shape = generated_images.shape[1:3]
    #print shape
    image = np.zeros((height*shape[0], width*shape[1]), dtype = generated_images.dtype)
    #print image.shape
    for index, img in enumerate(generated_images):
        #print index, img.shape
        i = int(index/width)
        j = index % width
        image[i*shape[0]:(i+1)*shape[0], j*shape[1]:(j+1)*shape[1]] = img[:, :, 0]
    return image


def train(BATCH_SIZE):
    (X_train, y_train), (X_test, y_test) = mnist.load_data()
    X_train = (X_train.astype(np.float32) - 127.5)/127.5
    #print X_train.shape
    X_train = X_train.reshape(X_train.shape[0], X_train.shape[1], X_train.shape[2], 1)
    #print X_train.shape
    
    discriminator = discriminator_model()
    generator = generator_model()
    #print generator.summary()
    #print discriminator.summary()
    #exit(0)
    discriminator_on_generator = \
        generator_containing_discriminator(generator, discriminator)
    #print discriminator_on_generator.summary()
    d_optim = SGD(lr=0.0005, momentum=0.9, nesterov=True)
    g_optim = SGD(lr=0.0005, momentum=0.9, nesterov=True)
    generator.compile(loss='binary_crossentropy', optimizer="SGD")
    discriminator_on_generator.compile(
        loss='binary_crossentropy', optimizer=g_optim)
    discriminator.trainable = True
    discriminator.compile(loss='binary_crossentropy', optimizer=d_optim)
    noise = np.zeros((BATCH_SIZE, 100))
    #print noise.shape
    for epoch in range(50):
        print "Epoch:", epoch, "of 100"
        print "Number of batches: ", int(X_train.shape[0]/BATCH_SIZE)

        for index in range(int(X_train.shape[0]/BATCH_SIZE)):
            #print "index in range:", int(X_train.shape[0]/BATCH_SIZE)
            # initializing uniform noise vector of 100 dimensions, between -1 and 1
            for i in range(BATCH_SIZE):
                noise[i, :] = np.random.uniform(-1, 1, 100)

            #print "Shape of noise:", noise.shape
            image_batch = X_train[index*BATCH_SIZE : (index+1)*BATCH_SIZE]
            #print "Shape of image batch:", image_batch.shape
            generated_images = generator.predict(noise, verbose=1)
            #generated_images = generated_images.reshape((generated_images.shape[0], 1) + generated_images.shape[1:-1])
            #print "Shape of generated image:", generated_images.shape
            if index % 20 == 0:
                image = combine_images(generated_images)
                image = image*127.5+127.5
                Image.fromarray(image.astype(np.uint8)).save("results/"+ \
                    str(epoch)+"_"+str(index)+".png")
                
            
            #print image_batch.shape
            #print generated_images.shape
            X = np.concatenate((image_batch, generated_images))
            y = [1] * BATCH_SIZE + [0] * BATCH_SIZE
            d_loss = discriminator.train_on_batch(X, y)
            print("batch %d d_loss : %f" % (index, d_loss))
            for i in range(BATCH_SIZE):
                noise[i, :] = np.random.uniform(-1, 1, 100)
            discriminator.trainable = False
            g_loss = discriminator_on_generator.train_on_batch(
                noise, [1] * BATCH_SIZE)
            discriminator.trainable = True
            print("batch %d g_loss : %f" % (index, g_loss))
            if index % 10 == 9:
                generator.save_weights('weights/generator', True)
                discriminator.save_weights('weights/discriminator', True)


def generate(BATCH_SIZE, nice=False):
    generator = generator_model()
    generator.compile(loss='binary_crossentropy', optimizer="SGD")
    generator.load_weights('generator')
    if nice:
        discriminator = discriminator_model()
        discriminator.compile(loss='binary_crossentropy', optimizer="SGD")
        discriminator.load_weights('discriminator')
        noise = np.zeros((BATCH_SIZE*20, 100))
        for i in range(BATCH_SIZE*20):
            noise[i, :] = np.random.uniform(-1, 1, 100)
        generated_images = generator.predict(noise, verbose=1)
        d_pret = discriminator.predict(generated_images, verbose=1)
        index = np.arange(0, BATCH_SIZE*20)
        index.resize((BATCH_SIZE*20, 1))
        pre_with_index = list(np.append(d_pret, index, axis=1))
        pre_with_index.sort(key=lambda x: x[0], reverse=True)
        nice_images = np.zeros((BATCH_SIZE, 1) +
                               (generated_images.shape[2:]), dtype=np.float32)
        for i in range(int(BATCH_SIZE)):
            idx = int(pre_with_index[i][1])
            nice_images[i, 0, :, :] = generated_images[idx, 0, :, :]
        image = combine_images(nice_images)
    else:
        noise = np.zeros((BATCH_SIZE, 100))
        for i in range(BATCH_SIZE):
            noise[i, :] = np.random.uniform(-1, 1, 100)
        generated_images = generator.predict(noise, verbose=1)
        image = combine_images(generated_images)
    image = image*127.5+127.5
    Image.fromarray(image.astype(np.uint8)).save(
        "generated_image.png")


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", type=str)
    parser.add_argument("--batch_size", type=int, default=128)
    parser.add_argument("--nice", dest="nice", action="store_true")
    parser.set_defaults(nice=False)
    args = parser.parse_args()
    return args

if __name__ == "__main__":
    args = get_args()
    if args.mode == "train":
        train(BATCH_SIZE=args.batch_size)
    elif args.mode == "generate":
        generate(BATCH_SIZE=args.batch_size, nice=args.nice)





