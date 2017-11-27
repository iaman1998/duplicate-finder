from collections import defaultdict
import os
import re
import time

import numpy as np
from tqdm import tqdm

from .hashnode import HashNode


def create_tree(root_path):
    root_node = HashNode(root_path[1:], is_file=False)
    # We need to save the nodes otherwise they will be lost outside the
    # method's scope.
    # TODO: Find another way to keep the nodes in memory
    nodes_by_path = {root_path: root_node}
    for (dirpath, dirnames, filenames) in tqdm(os.walk(root_path)):
        parent_node = nodes_by_path[dirpath]
        items = [(name, False) for name in dirnames] + \
                [(name, True) for name in filenames]
        for name, is_file in items:
            node = HashNode(name, parent=parent_node)
            path = os.path.join(dirpath, name)
            nodes_by_path[path] = node
    return nodes_by_path


def group_nodes_by_hash(root_paths, nodes_by_path,
                        skip_duplicates_children=False):
    print('Computing hashes and regrouping nodes...')
    start = time.time()
    nodes_by_hash = defaultdict(list)

    # Traverse the tree
    nodes_to_explore = [nodes_by_path[path] for path in root_paths]
    while len(nodes_to_explore) > 0:
        node = nodes_to_explore.pop()
        if not (skip_duplicates_children and node.hash_md5 in nodes_by_hash):
            # We only explore the children for that have no duplicates.
            # The children of duplicate nodes will indeed be nested duplicates
            nodes_to_explore.extend(node.children)
        nodes_by_hash[node.hash_md5].append(node)
    print('\t{:.2f}s'.format(time.time() - start))
    return nodes_by_hash


def explore_paths(paths):
    nodes_by_path = {}
    print('Discovering files...')
    for path in paths:
        # Create tree
        print('\t{}'.format(path))
        assert os.path.exists(path), '{} does not exist'.format(path)
        nodes_by_path.update(create_tree(path))
    return nodes_by_path


def size_to_str(size):
    return '{:0.2f} MB'.format(size/1e6)


def find_matching_nodes(pattern, nodes_by_path):
    return [node for path, node in nodes_by_path.items()
            if re.search(pattern, path, re.IGNORECASE)]


def find_duplicates(root_paths):
    nodes_by_path = explore_paths(root_paths)

    # Regroup nodes by hash
    nodes_by_hash = group_nodes_by_hash(root_paths,
                                        nodes_by_path,
                                        skip_duplicates_children=True)
    duplicate_hashes = [k for k, v in nodes_by_hash.items() if len(v) > 1]

    # Compute duplicate sizes for each duplicate
    print('Getting duplicates sizes...')
    start = time.time()
    duplicated_sizes = []
    for hash_val in duplicate_hashes:
        duplicate_nodes = nodes_by_hash[hash_val]
        nb_duplicates = len(duplicate_nodes) - 1
        duplicated_size = nb_duplicates * duplicate_nodes[0].storage_size
        duplicated_sizes.append(duplicated_size)
    print('\t{:.2f}s'.format(time.time() - start))

    print('Sorting duplicates...')
    # Sort and print duplicated nodes by size
    for idx in np.argsort(duplicated_sizes)[::-1][:100]:
        nodes = nodes_by_hash[duplicate_hashes[idx]]
        print(size_to_str(duplicated_sizes[idx]))
        print(''.join(['\t{}\n'.format(node.storage_path) for node in nodes]))
