# -*- coding: utf-8 -*-
# @Author: bo.shi
# @Date:   2019-12-30 19:26:53
# @Last Modified by:   bo.shi
# @Last Modified time: 2020-01-01 11:39:23
""" CLUE processors and helpers """

import logging
import os
import torch
# from .utils import DataProcessor, InputExample, InputFeatures
import csv
import sys
import copy
import json

logger = logging.getLogger(__name__)



class InputExample(object):
    """
    A single training/test example for simple sequence classification.

    Args:
        guid: Unique id for the example.
        text_a: string. The untokenized text of the first sequence. For single
        sequence tasks, only this sequence must be specified.
        text_b: (Optional) string. The untokenized text of the second sequence.
        Only must be specified for sequence pair tasks.
        label: (Optional) string. The label of the example. This should be
        specified for train and dev examples, but not for test examples.
    """
    def __init__(self, guid, text_a, text_b=None, label=None, ent1=None, ent2=None):
        self.guid = guid
        self.text_a = text_a
        self.text_b = text_b
        self.label = label
        self.ent1 = ent1
        self.ent2 = ent2

    def __repr__(self):
        return str(self.to_json_string())

    def to_dict(self):
        """Serializes this instance to a Python dictionary."""
        output = copy.deepcopy(self.__dict__)
        return output

    def to_json_string(self):
        """Serializes this instance to a JSON string."""
        return json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n"


class InputFeatures(object):
    """
    A single set of features of data.

    Args:
        input_ids: Indices of input sequence tokens in the vocabulary.
        attention_mask: Mask to avoid performing attention on padding token indices.
            Mask values selected in ``[0, 1]``:
            Usually  ``1`` for tokens that are NOT MASKED, ``0`` for MASKED (padded) tokens.
        token_type_ids: Segment token indices to indicate first and second portions of the inputs.
        label: Label corresponding to the input
    """

    def __init__(self, input_ids, attention_mask, token_type_ids, label,input_len):
        self.input_ids = input_ids
        self.attention_mask = attention_mask
        self.token_type_ids = token_type_ids
        self.input_len = input_len
        self.label = label

    def __repr__(self):
        return str(self.to_json_string())

    def to_dict(self):
        """Serializes this instance to a Python dictionary."""
        output = copy.deepcopy(self.__dict__)
        return output

    def to_json_string(self):
        """Serializes this instance to a JSON string."""
        return json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n"


SPIECE_UNDERLINE = "???"

def _is_chinese_char(cp):
    if ((cp >= 0x4E00 and cp <= 0x9FFF) or  #
            (cp >= 0x3400 and cp <= 0x4DBF) or  #
            (cp >= 0x20000 and cp <= 0x2A6DF) or  #
            (cp >= 0x2A700 and cp <= 0x2B73F) or  #
            (cp >= 0x2B740 and cp <= 0x2B81F) or  #
            (cp >= 0x2B820 and cp <= 0x2CEAF) or
            (cp >= 0xF900 and cp <= 0xFAFF) or  #
            (cp >= 0x2F800 and cp <= 0x2FA1F)):  #
        return True

    return False

def is_fuhao(c):
    if c == "???" or c == "???" or c == "???" or c == "???" or c == "???" or c == "???" or c == "???" or c == "???" or c == "???" \
            or c == "???" or c == "~" or c == "???" or c == "???" or c == "???" or c == "," or c == "???" or c == "'" or c == "???" or c == "???" \
            or c == "$" or c == "???" or c == "???" or c == "???" or c == ";" or c == "???" or c == "(" or c == ")" or c == "-" or c == "???" or c == "???" \
            or c == "???" or c == "???":
        return True
    return False

def _tokenize_chinese_chars(text):
    """Adds whitespace around any CJK character."""
    output = []
    for char in text:
        cp = ord(char)
        if _is_chinese_char(cp) or is_fuhao(char):
            if len(output) > 0 and output[-1] != SPIECE_UNDERLINE:
                output.append(SPIECE_UNDERLINE)
            output.append(char)
            output.append(SPIECE_UNDERLINE)
        else:
            output.append(char)
    return "".join(output)

def is_whitespace(c):
    if c == " " or c == "\t" or c == "\r" or c == "\n" or ord(c) == 0x202F or c == SPIECE_UNDERLINE:
        return True
    return False

def whitespace_tokenize(text):
    """Runs basic whitespace cleaning and splitting on a peice of text."""
    text = text.strip()
    if not text:
        return []
    tokens = text.split()
    return tokens



class DataProcessor(object):
    """Base class for data converters for sequence classification data sets."""

    def get_train_examples(self, data_dir):
        """Gets a collection of `InputExample`s for the train set."""
        raise NotImplementedError()

    def get_dev_examples(self, data_dir):
        """Gets a collection of `InputExample`s for the dev set."""
        raise NotImplementedError()

    def get_labels(self):
        """Gets the list of labels for this data set."""
        raise NotImplementedError()

    def get_verbalizers(self):
        """Gets the verbalizers for this data set."""
        raise NotImplementedError()

    @classmethod
    def _read_tsv(cls, input_file, quotechar=None):
        """Reads a tab separated value file."""
        with open(input_file, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f, delimiter="\t", quotechar=quotechar)
            lines = []
            for line in reader:
                lines.append(line)
            return lines

    @classmethod
    def _read_json(cls, input_file):
        """Reads a json list file."""
        with open(input_file, "r") as f:
            reader = f.readlines()
            lines = []
            for line in reader:
                lines.append(json.loads(line.strip()))
            return lines

    @classmethod
    def _read_mrc_json(cls, input_file):
        """Reads a json list file."""
        with open(input_file, "r") as f:
            train_data = json.load(f)
            train_data = train_data["data"]
        return train_data


def collate_fn(batch):
    """
    batch should be a list of (sequence, target, length) tuples...
    Returns a padded tensor of sequences sorted from longest to shortest,
    """
    all_input_ids, all_attention_mask, all_token_type_ids, all_lens, all_labels = map(torch.stack, zip(*batch))
    max_len = max(all_lens).item()
    all_input_ids = all_input_ids[:, :max_len]
    all_attention_mask = all_attention_mask[:, :max_len]
    all_token_type_ids = all_token_type_ids[:, :max_len]
    return all_input_ids, all_attention_mask, all_token_type_ids, all_labels


def xlnet_collate_fn(batch):
    """
    batch should be a list of (sequence, target, length) tuples...
    Returns a padded tensor of sequences sorted from longest to shortest,
    """
    all_input_ids, all_attention_mask, all_token_type_ids, all_lens, all_labels = map(torch.stack, zip(*batch))
    max_len = max(all_lens).item()
    all_input_ids = all_input_ids[:, -max_len:]
    all_attention_mask = all_attention_mask[:, -max_len:]
    all_token_type_ids = all_token_type_ids[:, -max_len:]
    return all_input_ids, all_attention_mask, all_token_type_ids, all_labels


def clue_convert_examples_to_features(examples, tokenizer,
                                      max_length=512,
                                      task=None,
                                      label_list=None,
                                      output_mode=None,
                                      pad_on_left=False,
                                      pad_token=0,
                                      pad_token_segment_id=0,
                                      mask_padding_with_zero=True):
    """
    Loads a data file into a list of ``InputFeatures``
    Args:
        examples: List of ``InputExamples`` or ``tf.data.Dataset`` containing the examples.
        tokenizer: Instance of a tokenizer that will tokenize the examples
        max_length: Maximum example length
        task: CLUE task
        label_list: List of labels. Can be obtained from the processor using the ``processor.get_labels()`` method
        output_mode: String indicating the output mode. Either ``regression`` or ``classification``
        pad_on_left: If set to ``True``, the examples will be padded on the left rather than on the right (default)
        pad_token: Padding token
        pad_token_segment_id: The segment ID for the padding token (It is usually 0, but can vary such as for XLNet where it is 4)
        mask_padding_with_zero: If set to ``True``, the attention mask will be filled by ``1`` for actual values
            and by ``0`` for padded values. If set to ``False``, inverts it (``1`` for padded values, ``0`` for
            actual values)

    Returns:
        If the input is a list of ``InputExamples``, will return
        a list of task-specific ``InputFeatures`` which can be fed to the model.

    """
    if task is not None:
        processor = clue_processors[task]()
        if label_list is None:
            label_list = processor.get_labels()
            logger.info("Using label list %s for task %s" % (label_list, task))
        if output_mode is None:
            output_mode = clue_output_modes[task]
            logger.info("Using output mode %s for task %s" % (output_mode, task))

    label_map = {label: i for i, label in enumerate(label_list)}

    features = []
    for (ex_index, example) in enumerate(examples):
        if ex_index % 10000 == 0:
            logger.info("Writing example %d" % (ex_index))

        inputs = tokenizer.encode_plus(
            example.text_a,
            example.text_b,
            add_special_tokens=True,
            max_length=max_length
        )
        input_ids, token_type_ids = inputs["input_ids"], inputs["token_type_ids"]

        # The mask has 1 for real tokens and 0 for padding tokens. Only real
        # tokens are attended to.
        attention_mask = [1 if mask_padding_with_zero else 0] * len(input_ids)
        input_len = len(input_ids)
        # Zero-pad up to the sequence length.
        padding_length = max_length - len(input_ids)
        if pad_on_left:
            input_ids = ([pad_token] * padding_length) + input_ids
            attention_mask = ([0 if mask_padding_with_zero else 1] * padding_length) + attention_mask
            token_type_ids = ([pad_token_segment_id] * padding_length) + token_type_ids
        else:
            input_ids = input_ids + ([pad_token] * padding_length)
            attention_mask = attention_mask + ([0 if mask_padding_with_zero else 1] * padding_length)
            token_type_ids = token_type_ids + ([pad_token_segment_id] * padding_length)

        assert len(input_ids) == max_length, "Error with input length {} vs {}".format(len(input_ids), max_length)
        assert len(attention_mask) == max_length, "Error with input length {} vs {}".format(len(attention_mask),
                                                                                            max_length)
        assert len(token_type_ids) == max_length, "Error with input length {} vs {}".format(len(token_type_ids),
                                                                                            max_length)
        if output_mode == "classification":
            label = label_map[example.label]
        elif output_mode == "regression":
            label = float(example.label)
        else:
            raise KeyError(output_mode)

        if ex_index < 5:
            logger.info("*** Example ***")
            logger.info("guid: %s" % (example.guid))
            logger.info("input_ids: %s" % " ".join([str(x) for x in input_ids]))
            logger.info("attention_mask: %s" % " ".join([str(x) for x in attention_mask]))
            logger.info("token_type_ids: %s" % " ".join([str(x) for x in token_type_ids]))
            logger.info("label: %s (id = %d)" % (example.label, label))
            logger.info("input length: %d" % (input_len))

        features.append(
            InputFeatures(input_ids=input_ids,
                          attention_mask=attention_mask,
                          token_type_ids=token_type_ids,
                          label=label,
                          input_len=input_len))
    return features


class TnewsProcessor(DataProcessor):
    """Processor for the TNEWS data set (CLUE version)."""

    def get_train_examples(self, data_dir):
        """See base class."""
        return self._create_examples(
            self._read_json(os.path.join(data_dir, "train.json")), "train")

    def get_dev_examples(self, data_dir):
        """See base class."""
        return self._create_examples(
            self._read_json(os.path.join(data_dir, "dev.json")), "dev")

    def get_test_examples(self, data_dir):
        """See base class."""
        return self._create_examples(
            self._read_json(os.path.join(data_dir, "test.json")), "test")

    def get_labels(self):
        """See base class."""
        labels = []
        for i in range(17):
            if i == 5 or i == 11:
                continue
            labels.append(str(100 + i))
        return labels

    def get_verbalizers(self):
        v = {
            100: ["??????"], 101: ["??????"], 102: ["??????"], 103: ["??????"], 104: ["??????"], 106: ["??????"], 107: ["??????"],
            108: ["??????"], 109: ["??????"], 110: ["??????"], 112: ["??????"], 113: ["??????"], 114: ["??????"], 115: ["??????"],
            116: ["??????"]
        }
        v = {str(key): value for key, value in v.items()}
        return v

    def _create_examples(self, lines, set_type):
        """Creates examples for the training and dev sets."""
        examples = []
        for (i, line) in enumerate(lines):
            guid = "%s-%s" % (set_type, i)
            text_a = line["sentence"]
            text_b = None
            label = str(line["label"]) if set_type != "test" else "100"
            examples.append(
                InputExample(guid=guid, text_a=text_a, text_b=text_b, label=label))
        return examples


class IflytekProcessor(DataProcessor):
    """Processor for the IFLYTEK data set (CLUE version)."""

    def get_train_examples(self, data_dir):
        """See base class."""
        return self._create_examples(
            self._read_json(os.path.join(data_dir, "train.json")), "train")

    def get_dev_examples(self, data_dir):
        """See base class."""
        return self._create_examples(
            self._read_json(os.path.join(data_dir, "dev.json")), "dev")

    def get_test_examples(self, data_dir):
        """See base class."""
        return self._create_examples(
            self._read_json(os.path.join(data_dir, "test.json")), "test")

    def get_labels(self):
        """See base class."""
        labels = []
        for i in range(119):
            labels.append(str(i))
        return labels

    def get_verbalizers(self):
        v = {
            0: ["??????"], 100: ["??????"], 101: ["??????"], 102: ["??????"], 103: ["??????"], 104: ["??????"], 105: ["??????"], 106: ["??????"],
            107: ["??????"], 108: ["??????"], 109: ["??????"], 10: ["??????"], 110: ["??????"], 111: ["??????"], 112: ["??????"], 113: ["??????"],
            114: ["??????"], 115: ["??????"], 116: ["??????"], 117: ["??????"], 118: ["??????"], 11: ["??????"], 12: ["??????"], 13: ["??????"],
            14: ["??????"], 15: ["??????"], 16: ["??????"], 17: ["??????"], 18: ["??????"], 19: ["??????"], 1: ["??????"], 20: ["??????"],
            21: ["??????"], 22: ["??????"], 23: ["??????"], 24: ["??????"], 25: ["??????"], 26: ["??????"], 27: ["??????"], 28: ["??????"],
            29: ["??????"], 2: ["??????"], 30: ["??????"], 31: ["??????"], 32: ["??????"], 33: ["??????"], 34: ["??????"], 35: ["??????"],
            36: ["??????"], 37: ["??????"], 38: ["??????"], 39: ["??????"], 3: ["??????"], 40: ["??????"], 41: ["??????"], 42: ["??????"],
            43: ["??????"], 44: ["??????"], 45: ["??????"], 46: ["??????"], 47: ["??????"], 48: ["??????"], 49: ["??????"], 4: ["??????"],
            50: ["??????"], 51: ["??????"], 52: ["??????"], 53: ["??????"], 54: ["??????"], 55: ["??????"], 56: ["??????"], 57: ["??????"],
            58: ["??????"], 59: ["??????"], 5: ["??????"], 60: ["??????"], 61: ["??????"], 62: ["??????"], 63: ["??????"], 64: ["??????"],
            65: ["??????"], 66: ["??????"], 67: ["??????"], 68: ["??????"], 69: ["??????"], 6: ["??????"], 70: ["??????"], 71: ["??????"],
            72: ["??????"], 73: ["??????"], 74: ["??????"], 75: ["??????"], 76: ["??????"], 77: ["??????"], 78: ["??????"], 79: ["??????"],
            7: ["??????"], 80: ["??????"], 81: ["??????"], 82: ["??????"], 83: ["??????"], 84: ["??????"], 85: ["??????"], 86: ["??????"],
            87: ["??????"], 88: ["??????"], 89: ["??????"], 8: ["??????"], 90: ["??????"], 91: ["??????"], 92: ["??????"], 93: ["??????"],
            94: ["??????"], 95: ["??????"], 96: ["??????"], 97: ["??????"], 98: ["??????"], 99: ["??????"], 9: ["??????"]
        }
        v = {str(key): value for key, value in v.items()}
        return v

    def _create_examples(self, lines, set_type):
        """Creates examples for the training and dev sets."""
        examples = []
        for (i, line) in enumerate(lines):
            guid = "%s-%s" % (set_type, i)
            text_a = line["sentence"]
            text_b = None
            label = str(line["label"]) if set_type != "test" else "0"
            examples.append(
                InputExample(guid=guid, text_a=text_a, text_b=text_b, label=label))
        return examples


class AfqmcProcessor(DataProcessor):
    """Processor for the AFQMC data set (CLUE version)."""

    def get_train_examples(self, data_dir):
        """See base class."""
        return self._create_examples(
            self._read_json(os.path.join(data_dir, "train.json")), "train")

    def get_dev_examples(self, data_dir):
        """See base class."""
        return self._create_examples(
            self._read_json(os.path.join(data_dir, "dev.json")), "dev")

    def get_test_examples(self, data_dir):
        """See base class."""
        return self._create_examples(
            self._read_json(os.path.join(data_dir, "test.json")), "test")

    def get_labels(self):
        """See base class."""
        return ["0", "1"]

    def get_verbalizers(self):
        return {
            "0": "?????????",
            "1": "??????",
        }

    def _create_examples(self, lines, set_type):
        """Creates examples for the training and dev sets."""
        examples = []
        for (i, line) in enumerate(lines):
            guid = "%s-%s" % (set_type, i)
            text_a = line["sentence1"]
            text_b = line["sentence2"]
            label = str(line["label"]) if set_type != "test" else "0"
            examples.append(
                InputExample(guid=guid, text_a=text_a, text_b=text_b, label=label))
        return examples

class OcnliProcessor(DataProcessor):
    """Processor for the CMNLI data set (CLUE version)."""

    def get_train_examples(self, data_dir):
        """See base class."""
        return self._create_examples(
            self._read_json(os.path.join(data_dir, "train.json")), "train")

    def get_dev_examples(self, data_dir):
        """See base class."""
        return self._create_examples(
            self._read_json(os.path.join(data_dir, "dev.json")), "dev")

    def get_test_examples(self, data_dir):
        """See base class."""
        return self._create_examples(
            self._read_json(os.path.join(data_dir, "test.json")), "test")

    def get_labels(self):
        """See base class."""
        return ["contradiction", "entailment", "neutral"]

    def get_verbalizers(self):
        return {
            "contradiction": "??????",
            "entailment": "??????",
            "neutral": "??????",
        }

    def _create_examples(self, lines, set_type):
        """Creates examples for the training and dev sets."""
        examples = []
        for (i, line) in enumerate(lines):
            guid = "%s-%s" % (set_type, i)
            text_a = line["sentence1"]
            text_b = line["sentence2"]
            label = str(line["label"]) if set_type != "test" else "neutral"
            if label.strip()=="-":
                continue
            examples.append(
                InputExample(guid=guid, text_a=text_a, text_b=text_b, label=label))
        return examples

class CmnliProcessor(DataProcessor):
    """Processor for the CMNLI data set (CLUE version)."""

    def get_train_examples(self, data_dir):
        """See base class."""
        return self._create_examples(
            self._read_json(os.path.join(data_dir, "train.json")), "train")

    def get_dev_examples(self, data_dir):
        """See base class."""
        return self._create_examples(
            self._read_json(os.path.join(data_dir, "dev.json")), "dev")

    def get_test_examples(self, data_dir):
        """See base class."""
        return self._create_examples(
            self._read_json(os.path.join(data_dir, "test.json")), "test")

    def get_labels(self):
        """See base class."""
        return ["contradiction", "entailment", "neutral"]

    def get_verbalizers(self):
        return {
            "contradiction": "??????",
            "entailment": "??????",
            "neutral": "??????",
        }

    def _create_examples(self, lines, set_type):
        """Creates examples for the training and dev sets."""
        examples = []
        for (i, line) in enumerate(lines):
            guid = "%s-%s" % (set_type, i)
            text_a = line["sentence1"]
            text_b = line["sentence2"]
            label = str(line["label"]) if set_type != "test" else "neutral"
            if label.strip()=="-":
                continue
            examples.append(
                InputExample(guid=guid, text_a=text_a, text_b=text_b, label=label))
        return examples


class CslProcessor(DataProcessor):
    """Processor for the CSL data set (CLUE version)."""

    def get_train_examples(self, data_dir):
        """See base class."""
        return self._create_examples(
            self._read_json(os.path.join(data_dir, "train.json")), "train")

    def get_dev_examples(self, data_dir):
        """See base class."""
        return self._create_examples(
            self._read_json(os.path.join(data_dir, "dev.json")), "dev")

    def get_test_examples(self, data_dir):
        """See base class."""
        return self._create_examples(
            self._read_json(os.path.join(data_dir, "test.json")), "test")

    def get_labels(self):
        """See base class."""
        return ["0", "1"]

    def get_verbalizers(self):
        return {
            "0": "??????",
            "1": "?????????",
        }

    def _create_examples(self, lines, set_type):
        """Creates examples for the training and dev sets."""
        examples = []
        for (i, line) in enumerate(lines):
            guid = "%s-%s" % (set_type, i)
            text_a = " ".join(line["keyword"])
            text_b = line["abst"]
            label = str(line["label"]) if set_type != "test" else "0"
            examples.append(
                InputExample(guid=guid, text_a=text_a, text_b=text_b, label=label))
        return examples


class WscProcessor(DataProcessor):
    """Processor for the WSC data set (CLUE version)."""

    def get_train_examples(self, data_dir):
        """See base class."""
        return self._create_examples(
            self._read_json(os.path.join(data_dir, "train.json")), "train")

    def get_dev_examples(self, data_dir):
        """See base class."""
        return self._create_examples(
            self._read_json(os.path.join(data_dir, "dev.json")), "dev")

    def get_test_examples(self, data_dir):
        """See base class."""
        return self._create_examples(
            self._read_json(os.path.join(data_dir, "test.json")), "test")

    def get_labels(self):
        """See base class."""
        return ["true", "false"]

    def get_verbalizers(self):
        return {
            "true": "??????",
            "false": "??????",
        }

    def _create_examples(self, lines, set_type):
        """Creates examples for the training and dev sets."""
        examples = []
        for (i, line) in enumerate(lines):
            guid = "%s-%s" % (set_type, i)
            text_a = line["text"]
            text_a_list = list(text_a)
            target = line["target"]
            query = target["span1_text"]
            query_idx = target["span1_index"]
            pronoun = target["span2_text"]
            pronoun_idx = target["span2_index"]
            assert text_a[pronoun_idx: (pronoun_idx + len(pronoun))] == pronoun, "pronoun: {}".format(pronoun)
            assert text_a[query_idx: (query_idx + len(query))] == query, "query: {}".format(query)
            if pronoun_idx > query_idx:
                text_a_list.insert(query_idx, "_")
                text_a_list.insert(query_idx + len(query) + 1, "_")
                text_a_list.insert(pronoun_idx + 2, "[")
                text_a_list.insert(pronoun_idx + len(pronoun) + 2 + 1, "]")
            else:
                text_a_list.insert(pronoun_idx, "[")
                text_a_list.insert(pronoun_idx + len(pronoun) + 1, "]")
                text_a_list.insert(query_idx + 2, "_")
                text_a_list.insert(query_idx + len(query) + 2 + 1, "_")
            text_a = "".join(text_a_list)
            text_b = None
            label = str(line["label"]) if set_type != "test" else "true"
            # if i == 0:
            #     print("target=", target)
            #     print("query=", query)
            #     print("pronoun=", pronoun)
            #     print("text_a=", text_a)
            #     print("label=", label)
            examples.append(
                InputExample(guid=guid, text_a=text_a, text_b=text_b, label=label, ent1=query, ent2=pronoun))
        return examples


class CopaProcessor(DataProcessor):
    """Processor for the COPA data set (CLUE version)."""

    def get_train_examples(self, data_dir):
        """See base class."""
        return self._create_examples(
            self._read_json(os.path.join(data_dir, "train.json")), "train")

    def get_dev_examples(self, data_dir):
        """See base class."""
        return self._create_examples(
            self._read_json(os.path.join(data_dir, "dev.json")), "dev")

    def get_test_examples(self, data_dir):
        """See base class."""
        return self._create_examples(
            self._read_json(os.path.join(data_dir, "test.json")), "test")

    def get_labels(self):
        """See base class."""
        return ["0", "1"]

    def _create_examples(self, lines, set_type):
        examples = []
        for (i, line) in enumerate(lines):
            i = 2 * i
            guid1 = "%s-%s" % (set_type, i)
            guid2 = "%s-%s" % (set_type, i + 1)
            premise = line["premise"]
            choice0 = line["choice0"]
            label = str(1 if line["label"] == 0 else 0) if set_type != "test" else "0"
            choice1 = line["choice1"]
            label2 = str(0 if line["label"] == 0 else 1) if set_type != "test" else "0"
            if line["question"] == "effect":
                text_a = premise
                text_b = choice0
                text_a2 = premise
                text_b2 = choice1
            elif line["question"] == "cause":
                text_a = choice0
                text_b = premise
                text_a2 = choice1
                text_b2 = premise
            else:
                raise ValueError(f"unknowed {line['question']} type")
            examples.append(
                InputExample(guid=guid1, text_a=text_a, text_b=text_b, label=label))
            examples.append(
                InputExample(guid=guid2, text_a=text_a2, text_b=text_b2, label=label2))
        return examples

    def _create_examples_version2(self, lines, set_type):
        """Creates examples for the training and dev sets."""
        examples = []
        for (i, line) in enumerate(lines):
            guid = "%s-%s" % (set_type, i)
            if line["question"] == "cause":
                text_a = line["premise"] + "??????????????????????????????" + line["choice0"]
                text_b = line["premise"] + "??????????????????????????????" + line["choice1"]
            else:
                text_a = line["premise"] + "???????????????????????????" + line["choice0"]
                text_b = line["premise"] + "???????????????????????????" + line["choice1"]
            label = str(1 if line["label"] == 0 else 0) if set_type != "test" else "0"
            examples.append(
                InputExample(guid=guid, text_a=text_a, text_b=text_b, label=label))
        return examples



class Cmrc2018Processor(DataProcessor):
    """Processor for the CMRC2018 data set (CLUE version)."""

    def get_train_examples(self, data_dir):
        """See base class."""
        return self._create_examples(
            self._read_mrc_json(os.path.join(data_dir, "train.json")), "train")

    def get_dev_examples(self, data_dir):
        """See base class."""
        return self._create_examples(
            self._read_mrc_json(os.path.join(data_dir, "dev.json")), "dev")

    def get_test_examples(self, data_dir):
        """See base class."""
        return self._create_examples(
            self._read_mrc_json(os.path.join(data_dir, "test.json")), "test")

    # def get_labels(self):
    #     """See base class."""
    #     return ["0", "1"]

    def _create_examples(self, lines, set_type):
        examples = []
        for line in lines:
            for paragraph in line["paragraphs"]:
                context = paragraph["context"].strip()
                for qa in paragraph["qas"]:
                    question = qa["question"].strip()
                    id_ = qa["id"]
                    answers = qa["answers"]
                    if set_type == "train":
                        # assert len(answers) == 1
                        examples.extend(
                            self.stride_split(id_, question, context, answers[0]["text"], answers[0]["answer_start"],
                                              is_train=1))
                    elif set_type == "dev":
                        answer_starts = [answer["answer_start"] for answer in answers]
                        answer_text = [answer["text"] for answer in answers]
                        o = self.stride_split(id_, question, context, answer_text[0], answer_starts[0], is_train=1)
                        for i in o:
                            i["answer_all"] = answer_text
                        examples.extend(o)
                    else:
                        examples.extend(self.stride_split(id_, question, context, "", -1))
        return examples

    def stride_split(self, i, q, c, a, s, is_train=0):
        self.max_len = 512
        self.doc_stride = 200
        """??????????????????context
        """
        # ????????????
        # q = lowercase_and_normalize(q)
        # c = lowercase_and_normalize(c)
        # b = lowercase_and_normalize(a)
        if a and a[0] == " ":
            a = a[1:]
            s = s + 1
        if a and a[-1] == " ":
            a = a[:-1]
        if a in ["????????????????????????????????????????????????????????????????????????????????????", "?????????????????????"]:
            s = s - 1

        e = s + len(a)
        # ????????????
        results, n = [], 0
        max_c_len = self.max_len - len(q) - 3
        while True:
            l, r = n * self.doc_stride, n * self.doc_stride + max_c_len
            if l <= s < e <= r:
                results.append({"id": i, "question": q, "content": c[l:r], "answer": a, "start": s - l, "end": e - l, "is_train": is_train})
            else:
                results.append({"id": i, "question": q, "content": c[l:r], "answer": "", "start": -1, "end": -1, "is_train": is_train})
            if r >= len(c):
                return results
            n += 1

def _create_examples_version2(self, lines, set_type):
        """Creates examples for the training and dev sets."""
        examples = []
        for (i, line) in enumerate(lines):
            guid = "%s-%s" % (set_type, i)
            if line["question"] == "cause":
                text_a = line["premise"] + "??????????????????????????????" + line["choice0"]
                text_b = line["premise"] + "??????????????????????????????" + line["choice1"]
            else:
                text_a = line["premise"] + "???????????????????????????" + line["choice0"]
                text_b = line["premise"] + "???????????????????????????" + line["choice1"]
            label = str(1 if line["label"] == 0 else 0) if set_type != "test" else "0"
            examples.append(
                InputExample(guid=guid, text_a=text_a, text_b=text_b, label=label))
        return examples


clue_tasks_num_labels = {
    "iflytek": 119,
    "cmnli": 3,
    "ocnli": 3,
    "afqmc": 2,
    "csl": 2,
    "wsc": 2,
    "copa": 2,
    "tnews": 15,
}

clue_processors = {
    "tnews": TnewsProcessor,
    # "iflytek": IflytekProcessor, # ?????????????????????mrc??????????????????
    "cmnli": CmnliProcessor,
    "ocnli": OcnliProcessor,
    "afqmc": AfqmcProcessor,
    "csl": CslProcessor,
    "wsc": WscProcessor,
    "copa": CopaProcessor,
    "cmrc": Cmrc2018Processor
}

clue_path = {
    "tnews": "tnews/",
    # "iflytek": "iflytek/",
    "cmnli": "cmnli/cmnli_public/",
    # "ocnli": "ocnli/",
    "afqmc": "afqmc/",
    "csl": "csl/",
    "wsc": "wsc/",
    # "copa": "copa/",
    "cmrc": "cmrc/"
}


clue_output_modes = {
    "tnews": "classification",
    "iflytek": "classification",
    "cmnli": "classification",
    "ocnli": "classification",
    "afqmc": "classification",
    "csl": "classification",
    "wsc": "classification",
    "copa": "classification",
    "cmrc": "mrc",
}


def get_all_data(base_path):
    all_training_data = dict() # ??????????????????????????????
    clue_train_data = dict()  # ????????????????????????
    clue_dev_data = dict() # ????????????????????????
    clue_test_data = dict() # ????????????????????????
    for clue_task, path in clue_path.items():
        # logger.info("reading dataset from {}".format(clue_task))
        print("reading dataset from {}".format(clue_task))
        processor = clue_processors[clue_task]()
        train_example = processor.get_train_examples(data_dir=os.path.join(base_path, path))
        dev_example = processor.get_dev_examples(data_dir=os.path.join(base_path, path))
        test_example = processor.get_test_examples(data_dir=os.path.join(base_path, path))

        if clue_output_modes[clue_task] == "classification":
            """
            {
                "classification": {
                    "tnews": {
                        "label_mappings": {"xx": "xx", ...}
                        data_list = [
                            {"ID": xx, "text_a": xx, "label": xx}
                        ]
                    }
                }
            }
            """
            label_mappings = processor.get_verbalizers()
            # labels = processor.get_labels()

            # training data
            if clue_task not in all_training_data.keys():
                all_training_data[clue_task] = dict()
            if clue_task not in all_training_data[clue_task].keys():
                all_training_data[clue_task][clue_task] = {
                    "label_mappings": label_mappings,
                    "data_list": list()
                }
                for example in train_example:
                    text_a = example.text_a
                    text_b = example.text_b
                    ID = example.guid
                    label = example.label
                    data_dict = {"ID": ID, "text_a": text_a, "label": label}
                    if clue_task == "wsc":
                        data_dict["span1_text"] = example.ent1
                        data_dict["span2_text"] = example.ent2
                    if text_b:
                        data_dict["text_b"] = text_b
                    all_training_data[clue_task][clue_task]["data_list"].append(data_dict)

            clue_train_data[clue_task] = {
                clue_task: {
                    clue_task: all_training_data[clue_task][clue_task]
                }
            }
            # dev data
            dev_data = {
                clue_task: {
                    clue_task: {
                        "label_mappings": label_mappings,
                        "data_list": list()
                    }
                }
            }
            for example in dev_example:
                text_a = example.text_a
                text_b = example.text_b
                ID = example.guid
                label = example.label
                data_dict = {"ID": ID, "text_a": text_a, "label": label}
                if clue_task == "wsc":
                    data_dict["span1_text"] = example.ent1
                    data_dict["span2_text"] = example.ent2
                if text_b:
                    data_dict["text_b"] = text_b
                dev_data[clue_task][clue_task]["data_list"].append(data_dict)
            clue_dev_data[clue_task] = dev_data

            # test data
            test_data = {
                clue_task: {
                    clue_task: {
                        "label_mappings": label_mappings,
                        "data_list": list()
                    }
                }
            }
            for example in test_example:
                text_a = example.text_a
                text_b = example.text_b
                ID = example.guid
                # label = example.label
                data_dict = {"ID": ID, "text_a": text_a, "label": ""}
                if clue_task == "wsc":
                    data_dict["span1_text"] = example.ent1
                    data_dict["span2_text"] = example.ent2
                if text_b:
                    data_dict["text_b"] = text_b
                test_data[clue_task][clue_task]["data_list"].append(data_dict)
            clue_test_data[clue_task] = test_data


        elif clue_output_modes[clue_task] == "mrc":
            """
            {
                "mrc": {
                    "cmrc": {
                        "label_mappings": {}
                        data_list = [
                            {"ID": xx, "context": xx, "question": xx, "answer": xx}
                        ]
                    }
                }
            }
            """
            # training data
            if clue_task not in all_training_data.keys():
                all_training_data[clue_task] = dict()
            if clue_task not in all_training_data[clue_task].keys():
                all_training_data[clue_task][clue_task] = {
                    "label_mappings": {},
                    "data_list": list()
                }
                for example in train_example:
                    question = example["question"]
                    context = example["content"]
                    ID = example["id"]
                    answer = example["answer"]
                    all_training_data[clue_task][clue_task]["data_list"].append(
                        {"ID": ID, "question": question, "context": context, "answer": answer}
                    )
            clue_train_data[clue_task] = {
                clue_task: {
                    clue_task: all_training_data[clue_task][clue_task]
                }
            }
            # dev data
            dev_data = {
                clue_task: {
                    clue_task: {
                        "label_mappings": {},
                        "data_list": list()
                    }
                }
            }
            for example in dev_example:
                question = example["question"]
                context = example["content"]
                ID = example["id"]
                answer = example["answer"]
                dev_data[clue_task][clue_task]["data_list"].append(
                    {"ID": ID, "question": question, "context": context, "answer": answer}
                )
            clue_dev_data[clue_task] = dev_data
            # test data
            test_data = {
                clue_task: {
                    clue_task: {
                        "label_mappings": {},
                        "data_list": list()
                    }
                }
            }
            for example in test_example:
                question = example["question"]
                context = example["content"]
                ID = example["id"]
                # answer = example["answer"]
                test_data[clue_task][clue_task]["data_list"].append(
                    {"ID": ID, "question": question, "context": context, "answer": ""}
                )
            clue_test_data[clue_task] = test_data
    return all_training_data, clue_train_data, clue_dev_data, clue_test_data
