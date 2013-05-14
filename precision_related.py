#-*- coding: UTF-8 -*-
from sklearn.preprocessing import normalize
from custom_setting import *
from name import *


def local_clustering(potential_duplicate_groups, coauthor_matrix):
    """Detect duplicate groups based on coauthor relationship between authors.

    Parameters:
        potential_duplicate_groups:
            A set containing lots of tuples describing the potential duplicate group.
        coauthor_matrix:
            A sparse matrix with row: author_id and column: author_id.
            It is obtained from author_paper_matrix.

    Returns:
        A set containing lots of tuples describing the real duplicate group.
    """
    real_duplicate_groups = set()
    print "\tIn total " + str(len(potential_duplicate_groups)) + " groups:"
    count = 0

    similarity_dict = dict()
    author_group_feature_dict = dict()
    normalized_author_group_feature_dict = dict()

    for group in potential_duplicate_groups:
        local_author_group_set = set()
        local_similarity_set = set()

        count += 1
        if count % 500 == 0:
            print "\tFinish analysing " \
                + str(float(count)/len(potential_duplicate_groups)*100) \
                + "% (" + str(count) + "/" + str(len(potential_duplicate_groups)) \
                + ") possible duplicate groups."
        # If there is only one author_id in the group, pass
        if len(group) == 1:
            real_duplicate_groups.add(group)
            continue

        # Treat coauthors for a particular author as features and normalize it
        for author in group:
            local_author_group_set.add((author,))
            if (author,) not in author_group_feature_dict:
                author_group_feature_dict[(author,)] = coauthor_matrix.getrow(author)
                normalized_author_group_feature_dict[(author,)] = normalize(
                    author_group_feature_dict[(author,)], norm='l2', axis=1)
        # Compute Cosine similarity between every pair of potential duplicate authors in the group
        for author_A in group:
            for author_B in group:
                if author_A < author_B:
                    local_similarity_set.add(((author_A,), (author_B,)))
                    if ((author_A,), (author_B,)) not in similarity_dict:
                        similarity_dict[((author_A,), (author_B,))] \
                            = (normalized_author_group_feature_dict[(author_A,)]
                                * normalized_author_group_feature_dict[(author_B,)].transpose())[0, 0]

        while True:
            max_similarity = 0
            max_pair = ()
            # Find the author partition pair with largest similarity
            # and it should be larger than then the threshold
            for author_group_pair in local_similarity_set:
                (max_similarity, max_pair) = (similarity_dict[author_group_pair], author_group_pair) \
                    if similarity_dict[author_group_pair] > merge_threshold else (max_similarity, max_pair)

            # If we cannot find such an author group pair,
            #   output the current duplicate authors in the whole group,
            # else
            #   we merge this pair
            if max_similarity == 0:
                for author_group in local_author_group_set:
                    real_duplicate_groups.add(author_group)
                break
            else:
                # Compute the new feature and normalize it for the merged author group pair
                new_author_group = tuple(sorted(max_pair[0] + max_pair[1]))
                if new_author_group not in author_group_feature_dict:
                    new_feature = author_group_feature_dict[max_pair[0]] + author_group_feature_dict[max_pair[1]]
                    author_group_feature_dict[new_author_group] = new_feature
                    normalized_author_group_feature_dict[new_author_group]\
                        = normalize(author_group_feature_dict[new_author_group], norm='l2', axis=1)

                # Remove individual author group in the new merged author group
                local_author_group_set.remove(max_pair[0])
                local_author_group_set.remove(max_pair[1])
                for author_group_pair in set(local_similarity_set):
                    if max_pair[0] in author_group_pair or max_pair[1] in author_group_pair:
                        local_similarity_set.remove(author_group_pair)
                # Compute new similarity between this new group
                # with the rest existing groups
                for author_group in local_author_group_set:
                    new_pair = tuple(sorted((author_group, new_author_group)))
                    local_similarity_set.add(new_pair)
                    if new_pair not in similarity_dict:
                        similarity_dict[new_pair] \
                            = (normalized_author_group_feature_dict[author_group]
                                * normalized_author_group_feature_dict[new_author_group].transpose())[0, 0]
                local_author_group_set.add(new_author_group)
    return real_duplicate_groups


def merge_local_clusters(real_duplicate_groups):
    """Merge local clusters.

    Parameters:
        real_duplicate_groups:
            A set of groups which contain duplicate author_ids separately.

    Returns:
        A dictionary of duplicate authors with key: author id and value:
        a list of duplicate author ids
    """
    id_group_dict = dict()
    print "\t Mapping each author to his/her duplicate authors from duplicate groups."
    for group in real_duplicate_groups:
        for author in group:
            id_group_dict.setdefault(author, list()).append(group)

    authors_duplicates_dict = dict()
    for (author_id, real_duplicate_groups) in id_group_dict.iteritems():
        union_group = set()
        for group in real_duplicate_groups:
            union_group = union_group.union(group)
        authors_duplicates_dict[author_id] = union_group

    return authors_duplicates_dict


def find_closure(authors_duplicates_dict):
    """Find the closure of duplicate authors for each author id.
       Example : {1: [1, 2, 3, 4], 2: [2, 3, 4, 5]} -> {1: [2, 3, 4, 5], 2: [1, 3, 4, 5]}

    Parameters:
        authors_duplicates_dict
            A dictionary of duplicate authors with key: author id and value:
            a list of duplicate author ids
    """
    print "\tFinding close duplicate author set for each author id."
    iteration = 0
    while True:
        print "\t\tIteration " + str(iteration)
        iteration += 1
        if iteration >= 100:
            break
        do_next_recursion = False
        for (author_id, duplicate_group) in authors_duplicates_dict.iteritems():
            changed = False
            final_duplicate_group = set(duplicate_group)
            for _author_id in duplicate_group:
                if duplicate_group != authors_duplicates_dict[_author_id]:
                    changed = True
                    do_next_recursion = True
                    final_duplicate_group = final_duplicate_group.union(authors_duplicates_dict[_author_id])
            if changed:
                authors_duplicates_dict[author_id] = set(final_duplicate_group)
                for _author_id in duplicate_group:
                    authors_duplicates_dict[_author_id] = set(final_duplicate_group)
        if do_next_recursion is False:
            break
    for author_id in authors_duplicates_dict.iterkeys():
        authors_duplicates_dict[author_id].remove(author_id)
