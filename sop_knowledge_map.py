import mammoth
from bs4 import BeautifulSoup
from pprint import pprint
import pydot
from os import listdir
from os.path import isfile, join

# Source: https://stackoverflow.com/questions/20656135/python-deep-merge-dictionary-data
def deep_merge_dicts(source, destination):
    """
    Deep merge dicts

    >>> a = { 'first' : { 'all_rows' : { 'pass' : 'dog', 'number' : '1' } } }
    >>> b = { 'first' : { 'all_rows' : { 'fail' : 'cat', 'number' : '5' } } }
    >>> merge(b, a) == { 'first' : { 'all_rows' : { 'pass' : 'dog', 'fail' : 'cat', 'number' : '5' } } }
    True
    """
    for key, value in source.items():
        if isinstance(value, dict):
            # get node or create one
            node = destination.setdefault(key, {})
            deep_merge_dicts(value, node)
        elif isinstance(value, list) and key in destination.keys():
            destination[key] = list(set(value + destination[key]))            
        else:
            destination[key] = value

    return destination

def nested_list_to_dict(ul, doc_words_setter):
    """Parse a list element from a SOP doc into a dict

    Parameters:
    ul (list element of BeautifulSoup): A HTML list element

    Returns:
    dict:The dict version of the list elment

    """
    level = {}
    lis = ul.findChildren('li' , recursive=False)

    for li in lis:
        child_ul = li.find('ul')
        text = li.next_element.strip()

        doc_words_setter(text)
        if child_ul == None:
            level[text] = {}
        else:
            level[text] = nested_list_to_dict(child_ul, doc_words_setter)

    return level

def file_to_html(file_path):
    """Parse a word doc into

    Parameters:
    file_path (str): The file path of a word doc

    Returns:
    BeautifulSoup page:The HTML page version of the word doc

    """
    f = open(file_path, 'rb')
    document = mammoth.convert_to_html(f)
    return BeautifulSoup(document.value.encode('utf8'))

def doc_to_dict(file_path):
    """Parse a word SOP doc into dict with its doc words

    Parameters:
    file_path (str): The file path of a word doc

    Returns:
    dict:A dict version of the SOP doc
    dict:A dict linking doc conditons and actions to the file paths

    """
    html = file_to_html(file_path)
    start = html.find('h1', string='call taker')
    event = {}
    doc_words = {}
    current_sit = None

    def set_doc_words(words):
        return (
            words not in doc_words.keys() and
                doc_words.update({words: [file_path]})
        )

    for element in start.next_elements:
        tag = element.name
        level = {}

        if tag == 'h1':
            break
        elif tag == 'h2':
            current_situation = element.text.strip()
            event[current_situation] = {}
        elif tag == 'p':
            next_next_element = element.next_element.next_element
            text = element.text.strip()

            set_doc_words(text)

            if next_next_element.name == 'ul':
                event[current_situation][text] = nested_list_to_dict(
                    next_next_element.find('ul'),
                    set_doc_words
                )
            else:
                event[current_situation][element.text] = {}

    return event, doc_words

def draw(graph, parent_name, child_name):
    """Draw an edge between a parent and a child

    Parameters:
    graph (pydot graph): The current Pydot graph
    parent_name (str): The parent node
    child_name (str): The child node


    Returns:
    pydot graph:The current Pydot graph

    """
    edge = pydot.Edge(parent_name, child_name)
    graph.add_edge(edge)

def visit(graph, node, parents=[], allowed_nodes=None):
    """Add a node branch to the graph

    Parameters:
    graph (pydot graph): The current Pydot graph
    node (dict): The branch
    parents (list): The list of parents to the branch
    allowed_nodes (list): The list of allowed nodes


    Returns:

    """
    for k,v in node.items():
        if len(parents) > 0 and (allowed_nodes == None or k in allowed_nodes):
            draw(graph, parents[-1], k)

        new_parents = parents.copy()

        if len(parents) == 0 or allowed_nodes == None or k in allowed_nodes:
            new_parents.append(k)

        visit(graph, v, new_parents, allowed_nodes)

def dict_to_graph(sop_dict, allowed_nodes=None):
    """Draw a graph with a SOP dict

    Parameters:
    sop_dict (dict): The dict version of a SOP doc
    allowed_nodes (list): The list of included node names


    Returns:
    pydot graph:The resultant Pydot graph

    """
    graph = pydot.Dot(graph_type='graph', rankdir='LR')
    visit(graph, sop_dict, allowed_nodes=allowed_nodes)

    return graph

def docs_to_dict(dir_path):
    """Translate a directory of SOP word docs into a dict

    Parameters:
    dir_path (str): The directory path


    Returns:
    dict:A dict version of the SOP docs
    dict:A dict linking doc conditons and actions to the file paths

    """
    files = [f for f in listdir(dir_path) if isfile(join(dir_path, f)) and '.docx' in f]
    dir_dict = {}
    doc_words = {}

    for file_path in files:
        file_dict, file_doc_words = doc_to_dict(dir_path + '/' + file_path)
        dir_dict = deep_merge_dicts(dir_dict, file_dict)
        doc_words = deep_merge_dicts(doc_words, file_doc_words)

    return dir_dict, doc_words

def filter_nodes(doc_words, doc_threshold = 2):
    """Filter node names with the maximum amount of files they are in

    Parameters:
    doc_words (dic): A dict of node names to SOP file paths
    doc_threshold (int): The maximum amount of files a node name can be in


    Returns:
    list:A list of included node names

    """
    allowed_nodes = []

    for k, v in doc_words.items():
        if len(v) <= doc_threshold:
            allowed_nodes.append(k)

    return allowed_nodes

# Examples:
#
# sop, doc_words = doc_to_dict("./data/A-ANIMAL.docx")
# graph = dict_to_graph(sop)
# graph.write_png('example1_graph.png')
#
# big_dict, file_doc_words = docs_to_dict('./data')
# graph = dict_to_graph(big_dict)
# graph.write_png('example2_graph.png')
#
# graph = dict_to_graph(
#    big_dict, filter_nodes(file_doc_words, doc_threshold=2)
# )