"""Test for susi.SOMClassifier

Usage:
python -m pytest tests/test_SOMClassifier.py

"""
import pytest
import os
import sys
import numpy as np
import itertools
from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.utils.estimator_checks import check_estimator
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import susi

# define test dataset
iris = load_iris()
X_train, X_test, y_train, y_test = train_test_split(
    iris.data, iris.target, test_size=0.3, random_state=42)

# preprocessing
scaler = StandardScaler()
X_train = scaler.fit_transform(X_train)
X_test = scaler.transform(X_test)

# data with missing labels -> semi-supervised
rng = np.random.RandomState(42)
random_unlabeled_points = rng.rand(len(y_train)) < 0.5
y_train_semi = np.copy(y_train)
y_train_semi[random_unlabeled_points] = -1

# SOM variables
TRAIN_MODES = ["online", "batch"]


@pytest.mark.parametrize("n_rows,n_columns,do_class_weighting", [
    (2, 2, True),
    (2, 2, False),
    (10, 20, True),
])
def test_init_super_som(n_rows, n_columns, do_class_weighting):
    random_state = 3
    som = susi.SOMClassifier(
        n_rows=n_rows,
        n_columns=n_columns,
        do_class_weighting=do_class_weighting,
        random_state=random_state)

    som.X_ = X_train
    som.y_ = y_train
    som.train_unsupervised_som()
    som.labeled_indices_ = list(range(len(som.y_)))
    som.set_bmus(som.X_)
    som.init_super_som()

    with pytest.raises(Exception):
        som = susi.SOMClassifier(
            init_mode_supervised="random")
        som.X_ = X_train
        som.y_ = y_train
        som.train_unsupervised_som()
        som.set_bmus(som.X_)
        som.init_super_som()


@pytest.mark.parametrize(
    ("n_rows,n_columns,learningrate,dist_weight_matrix,random_state,"
     "class_weight,expected"), [
        (2, 2, 0.3, np.array([[1.3, 0.4], [2.1, 0.2]]).reshape(2, 2, 1),
         3, 1., None),
        (2, 2, 1e-9, np.array([[1.3, 0.4], [2.1, 0.2]]).reshape(2, 2, 1),
         3, 1., np.array([[False, False], [False, False]])),
     ])
def test_change_class_proba(n_rows, n_columns, learningrate,
                            dist_weight_matrix, random_state, class_weight,
                            expected):
    som = susi.SOMClassifier(n_rows=n_rows, n_columns=n_columns,
                             random_state=random_state)
    # som.classes_ = [0, 1, 2]
    # som.class_weights_ = [1., 1., 1.]
    new_som_array = som.change_class_proba(learningrate, dist_weight_matrix,
                                           class_weight)
    assert(new_som_array.shape == (n_rows, n_columns, 1))
    assert(new_som_array.dtype == bool)
    if expected is not None:
        assert np.array_equal(new_som_array, expected.reshape((2, 2, 1)))


@pytest.mark.parametrize(
    ("n_rows,n_columns,learningrate,dist_weight_matrix,som_array,"
     "random_state,true_vector"), [
        (2, 2, 0.3, np.array([[1.3, 0.4], [2.1, 0.2]]).reshape(2, 2, 1),
         np.array([[1.3, 0.4], [2.1, 0.2]]).reshape(2, 2, 1), 3,
         np.array([1])),
     ])
def test_modify_weight_matrix_supervised(
        n_rows, n_columns, learningrate, dist_weight_matrix, som_array,
        random_state, true_vector):
    som = susi.SOMClassifier(
        n_rows=n_rows,
        n_columns=n_columns,
        random_state=random_state)
    som.classes_ = [0, 1, 2]
    som.class_weights_ = [1., 1., 1.]
    som.super_som_ = som_array
    new_som = som.modify_weight_matrix_supervised(
        dist_weight_matrix=dist_weight_matrix,
        true_vector=true_vector,
        learningrate=learningrate)
    assert(new_som.shape == (n_rows, n_columns, 1))


@pytest.mark.parametrize(
    "train_mode_unsupervised,train_mode_supervised",
    itertools.product(TRAIN_MODES, TRAIN_MODES))
def test_fit(train_mode_unsupervised, train_mode_supervised):
    som = susi.SOMClassifier(
        n_rows=5,
        n_columns=5,
        train_mode_unsupervised=train_mode_unsupervised,
        train_mode_supervised=train_mode_supervised,
        random_state=3)
    som.fit(X_train, y_train)
    assert(som.score(X_test, y_test) > 0.9)


def test_estimator_status():
    check_estimator(susi.SOMClassifier)


@pytest.mark.parametrize(
    "train_mode_unsupervised,train_mode_supervised",
    itertools.product(TRAIN_MODES, TRAIN_MODES))
def test_fit_semi(train_mode_unsupervised, train_mode_supervised):
    som = susi.SOMClassifier(
        n_rows=5,
        n_columns=5,
        train_mode_unsupervised=train_mode_unsupervised,
        train_mode_supervised=train_mode_supervised,
        missing_label_placeholder=-1,
        random_state=3)
    som.fit(X_train, y_train_semi)
    assert(som.score(X_test, y_test) > 0.5)
