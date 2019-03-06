"""Utilities for sparse binary merkle trees.

Merkle trees are represented as sequences of layers, from root to leaves. The root layer contains
only a single element, the leaves as many as there are data items in the tree. The data itself is
not considered to be part of the tree.
"""

from typing import (
    Iterable,
    Sequence,
    Union,
)

from cytoolz import (
    iterate,
    take,
)
from eth2._utils.tuple import update_tuple_item
from eth2.beacon._utils.hash import (
    hash_eth2,
)
from eth_typing import (
    Hash32,
)
from eth_utils import (
    ValidationError,
)

from .merkle_normal import (  # noqa: F401
    _calc_parent_hash,
    _hash_layer,
    get_branch_indices,
    get_root,
    MerkleTree,
    MerkleProof,
)


TreeHeight = 32
EmptyNodeHashes = tuple(
    take(TreeHeight, iterate(lambda node_hash: hash_eth2(node_hash + node_hash), b'\x00' * 32))
)


def get_merkle_proof(tree: MerkleTree, item_index: int) -> Iterable[Hash32]:
    """
    Read off the Merkle proof for an item from a Merkle tree.
    """
    if item_index < 0 or item_index >= len(tree[-1]) or tree[-1][item_index] == EmptyNodeHashes[0]:
        raise ValidationError("Item index out of range")

    branch_indices = get_branch_indices(item_index, len(tree))
    proof_indices = [i ^ 1 for i in branch_indices][:-1]  # get sibling by flipping rightmost bit
    return tuple(
        layer[proof_index]
        for layer, proof_index
        in zip(reversed(tree), proof_indices)
    )


def verify_merkle_proof(root: Hash32,
                        leaf: Hash32,
                        index: int,
                        proof: MerkleProof) -> bool:
    """
    Verify that the given ``item`` is on the merkle branch ``proof``
    starting with the given ``root``.
    """
    assert len(proof) == TreeHeight
    value = leaf
    for i in range(TreeHeight):
        if index // (2**i) % 2:
            value = hash_eth2(proof[i] + value)
        else:
            value = hash_eth2(value + proof[i])
    return value == root


def calc_merkle_tree(items: Sequence[Union[bytes, bytearray]]) -> MerkleTree:
    """
    Calculate the Merkle tree corresponding to a list of items.
    """
    leaves = tuple(hash_eth2(item) for item in items)
    return calc_merkle_tree_from_leaves(leaves)


def get_merkle_root_from_items(items: Sequence[Union[bytes, bytearray]]) -> Hash32:
    """
    Calculate the Merkle root corresponding to a list of items.
    """
    return get_root(calc_merkle_tree(items))


def calc_merkle_tree_from_leaves(leaves: Sequence[Hash32]) -> MerkleTree:
    if len(leaves) == 0:
        raise ValueError("No leaves given")
    tree = tuple()  # type: ignore
    tree = (leaves,) + tree
    for i in range(TreeHeight):
        if len(tree[0]) % 2 == 1:
            tree = update_tuple_item(tree, 0, tree[0] + (EmptyNodeHashes[i],))
        tree = (_hash_layer(tree[0]),) + tree
    return tree


def get_merkle_root(leaves: Sequence[Hash32]) -> Hash32:
    """
    Return the Merkle root of the given 32-byte hashes.
    """
    return get_root(calc_merkle_tree_from_leaves(leaves))
