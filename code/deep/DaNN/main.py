import torch
import torch.nn as nn
import torch.optim as optim
import torchvision
from torch.autograd import Variable
import torch.nn.functional as F
import data_loader
import DaNN
import mmd
import numpy as np

CUDA = True if torch.cuda.is_available() else False
LEARNING_RATE = 0.02
MOMEMTUN = 0.05
L2_WEIGHT = 0.003
DROPOUT = 0.5
N_EPOCH = 900
BATCH_SIZE = [64, 64]
LAMBDA = 0.25
GAMMA = 10 ^ 3
RESULT_TRAIN = []
RESULT_TEST = []
log_train = open('log_train.txt', 'w')
log_test = open('log_test.txt', 'w')


def mmd_loss(x_src, x_tar):
    return mmd.mix_rbf_mmd2(x_src, x_tar, [GAMMA])


def train(model, optimizer, epoch, data_src, data_tar):
    total_loss_train = 0
    criterion = nn.CrossEntropyLoss()
    correct = 0
    batch_j = 0
    list_src, list_tar = list(enumerate(data_src)), list(enumerate(data_tar))
    for batch_id, (data, target) in enumerate(data_src):
        _, (x_tar, y_target) = list_tar[batch_j]
        if batch_id >= len(list_src) - 1:
            break
        batch_j = batch_j + 1 if batch_j < len(list_tar) - 2 else 0
        if CUDA:
            model = model.cuda()
            data, target = data.cuda(), target.cuda()
            x_tar, y_target = x_tar.cuda(), y_target.cuda()
        model.train()
        data, target = Variable(data.view(-1, 28 * 28)), Variable(target)
        x_tar, y_target = Variable(x_tar.view(-1, 28 * 28)), Variable(y_target)
        y_src, x_src_mmd, x_tar_mmd = model(data, x_tar)

        loss_c = criterion(y_src, target)
        loss_mmd = mmd_loss(x_src_mmd, x_tar_mmd)
        pred = y_src.data.max(1)[1]  # get the index of the max log-probability
        correct += pred.eq(target.data.view_as(pred)).cpu().sum()
        loss = loss_c + LAMBDA * loss_mmd
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        total_loss_train += loss.data[0]
        res_i = 'Epoch: [{}/{}], Batch: [{}/{}], loss: {:.6f}'.format(
            epoch, N_EPOCH, batch_id + 1, len(data_src), loss.data[0]
        )
        print(res_i)
    total_loss_train /= len(data_src)
    acc = correct * 100. / len(data_src.dataset)
    res_e = 'Epoch: [{}/{}], training loss: {:.6f}, correct: [{}/{}], training accuracy: {:.4f}%'.format(
        epoch, N_EPOCH, total_loss_train, correct, len(data_src.dataset), acc
    )
    print(res_e)
    log_train.write(res_e + '\n')
    RESULT_TRAIN.append([epoch, total_loss_train, acc])
    return model


def test(model, data_tar, epoch):
    total_loss_test = 0
    correct = 0
    criterion = nn.CrossEntropyLoss()
    for batch_id, (data, target) in enumerate(data_tar):
        if CUDA:
            model = model.cuda()
            data, target = data.cuda(), target.cuda()
        model.eval()
        data, target = Variable(data.view(-1, 28 * 28), volatile=True), Variable(target)
        ypred, _, _ = model(data, data)
        loss = criterion(ypred, target)
        pred = ypred.data.max(1)[1]  # get the index of the max log-probability
        correct += pred.eq(target.data.view_as(pred)).cpu().sum()
        total_loss_test += loss.data[0]
    accuracy = correct * 100. / len(data_tar.dataset)
    res = 'Test: total loss: {:.6f}, correct: [{}/{}], testing accuracy: {:.4f}%'.format(
        total_loss_test, correct, len(data_tar.dataset), accuracy
    )
    print(res)
    RESULT_TEST.append([e, total_loss_test, accuracy])
    log_test.write(res + '\n')


if __name__ == '__main__':
    rootdir = '../data/office_caltech_10/'
    torch.manual_seed(1)
    data_src = data_loader.load_data(
        root_dir=rootdir, domain='amazon', batch_size=BATCH_SIZE[0])
    data_tar = data_loader.load_data(
        root_dir=rootdir, domain='webcam', batch_size=BATCH_SIZE[1])
    model = DaNN.DaNN(n_input=28 * 28, n_hidden=256, n_class=10)
    optimizer = optim.SGD(
        model.parameters(),
        lr=LEARNING_RATE,
        momentum=MOMEMTUN,
        weight_decay=L2_WEIGHT
    )
    for e in range(1, N_EPOCH + 1):
        model = train(model=model, optimizer=optimizer,
                      epoch=e, data_src=data_src, data_tar=data_tar)
        test(model, data_tar, e)
    torch.save(model, 'model_dann.pkl')
    log_train.close()
    log_test.close()
    res_train = np.asarray(RESULT_TRAIN)
    res_test = np.asarray(RESULT_TEST)
    np.savetxt('res_train.csv', res_train, fmt='%.6f', delimiter=',')
    np.savetxt('res_test.csv', res_test, fmt='%.6f', delimiter=',')
