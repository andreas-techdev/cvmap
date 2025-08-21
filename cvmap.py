# -*- coding: utf-8 -*-
"""
cvmap takes (any) SVG graphics and allows to manipulate the text-tags. 
Intended use was to take a Mindmap created with Freemind summarizing my personal CV and add balloons and links 

Basic useage: 
    - Create a mindmap with Freemind and export it as svg
    - run cvmap (replace filename in the code below)
    - Now you have got a .toml-file you can edit. Add any balloons and links
    - Run cvmap once again, open the ..._with_balloons.svg or the created html-file and enjoy.
 
Example file: see examples. This script transforms examples/tintin.svg   to tintin_with_balloons.svg
 
Created on Aug  12 2025

@author: andreas_techdev

TODO
 - add file input dialogue / command line interface
 - change print statements to logger calls
 - put default globals in config file
 
"""
import xml.etree.ElementTree as ET
import re
import os, shutil, sys
import tomli, tomli_w



#######################################################
# Config and Input - to be cleaned up later
######################################################

#### PUT YOUR FILENAME HERE #######
filename= './example/CVTintin.svg'
filename_woextension, _ = os.path.splitext(filename)
fieldnames = ["element", "balloon", "link"]
SVG_NAMESPACE_URI = "http://www.w3.org/2000/svg"
ET.register_namespace('', SVG_NAMESPACE_URI) 
XLINK_NAMESPACE_URI = "http://www.w3.org/1999/xlink"
ET.register_namespace('xlink', XLINK_NAMESPACE_URI)
encoding = 'utf-8' 

    
def ReadSVG(filename): 
    '''
    Reads and parses and SVG file
    Inputs:
        filename: String, the file to parse
    outputs
        root: the xml root of the file
        element_list: A list of strings which could be found in the file in the <text> elements
        
    '''
    
    try:
        tree = ET.parse(filename)
        root = tree.getroot()
    except FileNotFoundError:
        print(f"file {filename} not found. Current working directory: {os.getcwd()}")
        sys.exit()
    except ET.ParseError as e:
        print(f"There was an error parsing the file: {e}")
        sys.exit()
    
    element_list = []
    # "text": Search for a <text> tag 
    text_elements_all = root.findall(f".//{{{SVG_NAMESPACE_URI}}}text")
    
    if not text_elements_all:
        print("No <text>-elements found in {filename}.")
    else:
        for text_element in text_elements_all:
            if text_element.text:  # check if any content
                element_list.append(text_element.text.strip())
            else:
                print("Information: Found empty text element, skipping this element.")
    return root, element_list

def read_toml_data(filename_toml):
    """
    Reads a TOML file (Array of Tables format) and returns its content as a list of dicts.
    Input:
        filename_toml: string, filename of the TOML file
    Output:
        toml_data: list of dicts, with the document content,
                   or an empty list if file doesn't exist or an error occurs.
    """
    if not os.path.exists(filename_toml):
        print(f"Info: File '{filename_toml}' doesn't exist. Returning an empty list.")
        return []

    toml_data = []
    try:
        with open(filename_toml, 'rb') as f: # 'rb' for read binary important here
            # tomli.load returns a Dictionary
            # We expect a dictionary containing a key
            # containing an array of tables (our list of dictionaries).
            parsed_data = tomli.load(f)

            if 'item' in parsed_data and isinstance(parsed_data['item'], list):
                toml_data = parsed_data['item']
            else:
                print(f"Warning: TOML file '{filename_toml}' does not contain an 'item' array or it's not a list. Returning empty list.")
                return []

        print(f"TOML-file '{filename_toml}' successfully read.")
    except Exception as e:
        print(f"File read error when reading '{filename_toml}': {e}\n Aborting.")
        #Exit gives the user a chance to fix file issues
        sys.exit()
    return toml_data

def write_toml_data(filename_toml, data):
    """
    Writes data to a TOML file as an Array of Tables.

    Inputs:
        filename_toml: String, the filename.
        data: List of dicts, the data to write. Each dict represents a table (row).
              Example: [{'element': 'Rollen', 'beschreibung': 'Ein Konzept'}]
    """
    if not data:
        print(f"No data provided for '{filename_toml}'. No file will be written.")
        return
    
    # tomli_w expects an array of dictionaries with this top level table we just by default call "item"
    array_name = 'item'
    data_to_write = {array_name: data}

    try:
        with open(filename_toml, 'wb') as f: #'wb' for binary write mode
            tomli_w.dump(data_to_write, f)
        print(f"Data successfully written to '{filename_toml}'.")
    except IOError as e:
        print(f"Write error when writing to file '{filename_toml}': {e}")
    except Exception as e: # Catch other potential errors from tomli_w.dump
        print(f"An unexpected error occurred while writing to '{filename_toml}': {e}")

    
def merge_file_data(data_fromtoml, element_list):
    """
    Merges and compares data from csv file and from svg
        - keeps balloons which are already existing
        - deletes rows which no longer exist in the SVG
        - adds new rows which are not yet in the csv file
    Parameters
    ----------
    data_fromtoml : list of dicts {fieldname: data} read from CSV file 
    element list : list of strings read from SVG file
       

    Returns
    -------
    data2write: ist of dicts {fieldname: data} finally to write to CSV

    """
    data2write = []
    
    # creating a set for processed keys
    processed_elements = set()
    # check existing data
    if data_fromtoml:
        for row in data_fromtoml:
            if row["element"] is not None and row["element"] in element_list:
                # Line exists in xml & svg --> keep xml line
                data2write.append(row)
                processed_elements.add(row['element'])
            else:
                #not in svg, but in csv --> outdated, delete
                print(f"Deleting the following line of the toml: {row}")
    # Adding new contents (all elements of element_list not processed so far)
    for element in element_list:
        if element not in processed_elements:
            data2write.append({fieldnames[0]: element, fieldnames[1]: "", fieldnames[2]: ""})
    
    return data2write

def modify_text_tags(root_element, data2write):
    """
    Modifies <text> tags based on a list of dictionaries.
    For each entry in data_to_write, it searches for a <text> tag
    whose text content matches the 'element' value and adds/updates
    a <title> tag with the 'balloon' value.

    Args:
        root_element: The root ET.Element of the XML tree.
        data_to_write: A list of dictionaries. Each dict should have
                       an 'element' key (for matching text content) and
                       a 'balloon' key (for the title tag content) and
                       a 'link' key (for the hyperlink).
    Returns:
        The modified root_element.
    """
    if root_element is None:
        print("Error: No root element provided for modification.")
        return None
    if not data2write:
        print("Warning: No data_to_write provided. No modifications will be made.")
        return root_element

    modified_count = 0
    
    # creation of a dict for rapid accesss to elements
    text_info_map = {}
    for entry in data2write:
        element_value = entry.get('element')
        balloon_value = entry.get('balloon')
        link_value = entry.get('link')

        # only add, if non-void elements exist
        if element_value and (balloon_value or link_value):
            text_info_map[element_value] = {
                'balloon': balloon_value if balloon_value else '', # Stelle sicher, dass es ein String ist
                'link': link_value if link_value else '' # Stelle sicher, dass es ein String ist
            }
    
    # Iteration of the parents
    for parent in root_element.iter():
        # Just iterate over relevant tags: these are tags directly under svg and und g (group) components
        if not isinstance(parent.tag, str) or parent.tag not in [
            f"{{{SVG_NAMESPACE_URI}}}svg",
            f"{{{SVG_NAMESPACE_URI}}}g"
        ]:
            continue 

        # Make a copy of the child list to modify
        for child_index, child in enumerate(list(parent)):
            # check if child tag is a <text> tag
            if child.tag == f"{{{SVG_NAMESPACE_URI}}}text":
                current_text_content = child.text 

                # Just go on if current text-tag contains content and if content is in our map
                if current_text_content and current_text_content in text_info_map:
                    info = text_info_map[current_text_content]
                    balloon_text = info['balloon']
                    link_url = info['link']

                    # Only modify, if there is a balloon or a link
                    if balloon_text or link_url:
                        print(f"Found <text> tag with content '{current_text_content}'. Modifying...")
                        modified_count += 1

                        # #####################################
                        # Creating the balloons
                        #######################################
                        # Remove existing <title>
                        existing_title = child.find('title')
                        if existing_title is not None:
                            child.remove(existing_title)
                        
                        original_text_content = child.text # store existing text
                        
                        # Add <title> if balloon text exists 
                        if balloon_text:
                            # Remove text as text goes into .tail
                            child.text = None 
                            title_tag_in_place = ET.Element('title')
                            title_tag_in_place.text = balloon_text # .text is the tag content in front of the first sub-tag
                            title_tag_in_place.tail = original_text_content # original text , .tail is the tag content behind the sub-tags
                            child.insert(0, title_tag_in_place) # insert this
                        else:
                            # If no balloon, reset to original content (important!)
                            child.text = original_text_content


                        ###########################################
                        # Creating links
                        #
                        # by wrapping <a> elements around
                        #####################################
                        
                        if link_url:
                            print(f"  Wrapping '{current_text_content}' in <a> link to '{link_url}'.")
                            a_tag = ET.Element('a', attrib={f"{{{XLINK_NAMESPACE_URI}}}href": link_url})
                            a_tag.set('target', '_blank') # open link in new tab

                            # Move the element to the new <a> tag
                            # 1. Remove old <text> tag
                            parent.remove(child)
                            # 2.insert <text> tag as a child of the <a> tag 
                            a_tag.append(child)
                            # 3. Insert the <a> tag at exactly the position of the original <text> tag
                            parent.insert(child_index, a_tag)
                        
                        # Debugging for the simple minded...
                        print(f"  Processed <text> tag '{current_text_content}': balloon={bool(balloon_text)}, link={bool(link_url)}")

    print(f"\nSummary: Modified {modified_count} tags in total.")
    return root_element
       
def get_parent(root, child):
    """
    Helper function that find the direct parent-element of a given child in an xml-tree
    
    Parameters
    ----------
    root : XML Root element of an xml-tree
        
    child : xml-tree-element
        The child we are searching the parent for

    Returns
    -------
    parent: the parent element (none if child is root)

    """
    # Iteration over  all elements (first the children of root, then the "grand-children"....)
    for parent in root.iter():
        # This loop is only needed to check if the child is directly one level lower
        for elem in parent:
            if elem is child:
                return parent
    return None

def get_inherited_fill_color(root_element):
    """
    Searches for the fill color of the first text tag in the SVG-element
    Considers the direct and inhereted 'fill' attribute and some style-tag rules (rudimentary and untested)

    Parameters
    ----------
    root_element : Root of an xml tree
        
    Returns
    -------
    string: fill attribute of element

    """
    default_color = "#000000"
    if root_element is None: return default_color
    
    #find the first <text> tag (triple {{{ to mask { in f-string)
    first_text_tag = next(root_element.iter(f"{{{SVG_NAMESPACE_URI}}}text"), None)
    
    if first_text_tag is None:
        print("No text tag found in SVG.")
        return default_color
    
    # make a list of all element going from first_text_tag up to root
    current_element = first_text_tag
    element_path = []
    while current_element is not None:
        element_path.append(current_element)
        #stop at root
        if current_element is root_element: break
        #next    
        current_element  = get_parent(root_element, current_element) 
        
        
    # go through this hierarchy 
    for elem in element_path:
       # check style attrib with priority
       if 'style' in elem.attrib:
           style_attr_value = elem.attrib('style')
           # regexp searches for fill with or without spaces and returns the value after the colon
           match = re.search(r"fill\s*:\s*([^;]+)", style_attr_value)
           if match: 
               print(f"Found colour in style attribute of {elem.tag} returning {elem.group(1).strip()}.")
               return elem.group(1).strip()
       #direct fill attrib?
       if 'fill' in elem.attrib:
           print(f"Found direct fill attribute. Element tag: {elem.tag} returning {elem.attrib['fill']}.")
           return elem.attrib['fill']
    # just in case
    print("No colour found - returning black.")
    return default_color

def add_explanation_text(
        root_element, 
        explanation_text = "Move your mouse over the element to see more details",
        position_offset = [20,20],
        font_size = 12, 
        additional_link = None        
        ):
    """
    Adds bottom left an extra-text to the svg picture and modifies height to avoid overlapping

    Parameters
    ----------
    root_element : xml root of the svg file
        
    explanation_text : STRING, optional
        DESCRIPTION. The text to place in the picture.
    position_offset : list of integers, optional
        DESCRIPTION. The distance of the text [x,y] from the margin.
    font_size : int, optional
        DESCRIPTION. The fontsize of the text.
    additional_link : List of 2 strings, optional
        DESCRIPTION. Shows an additional link on the bottom [link, display_text].

    Returns
    -------
    The modified root element

    """
    if root_element is None: 
        print("Error: No SVG root element provided to add explanation text.")
        return None
    
    
    # trying to get width and height
    try: 
        #svg_width = int(root_element.get('width', '300'))
        svg_height = int(root_element.get('height', '400'))
    except ValueError:
        print("Warning: Could not parse SVG width/height. Using default values.")
        #svg_width = 300
        svg_height = 400
    
    text_x_coord = str(position_offset[0])
    if not isinstance(explanation_text, list): 
        explanation_text = [explanation_text]
    
    # calculate y-position for first line
    #
    # y postion = svg_height - position_offset[1]
    #               - (number of lines)*text_height
    #               - text height if additional link is not none
    text_height_em = 1.2 # approx text height in em
    if additional_link:
        num_lines = len(explanation_text) +1
    else:
        num_lines = len(explanation_text)
    line_spacing_px = font_size*text_height_em
    
    svg_height += num_lines*line_spacing_px+position_offset[1]
    root_element.set('height', str(svg_height))
    
    text_y_firstline = svg_height - position_offset[1] - num_lines*line_spacing_px
    
    fill_color = get_inherited_fill_color(root_element) # make it the same colour as the rest of the text
    # make a blueprint of each text element#
    explanation_text_elem = ET.Element(
        f"{{{SVG_NAMESPACE_URI}}}text",
        attrib={
            'x': text_x_coord,
            'y': str(text_y_firstline),
            'font-size': str(font_size),
            'fill': fill_color,
            'font-family': 'Arial, sans-serif',
            'stroke': 'none',
            'stroke-width': '0'
        }
    )
    
    for i,line in enumerate(explanation_text):
        # work with tspan and Subelement for each line - relatively spaced to the previous
        tspan_attr = {'x': text_x_coord}
        if i==0:
            tspan_attr['dy'] = "0em" 
        else:
            tspan_attr['dy'] = str(text_height_em)
        tspan_element = ET.SubElement(
            explanation_text_elem,
            f"{{{SVG_NAMESPACE_URI}}}tspan",
            attrib = tspan_attr
        )
        tspan_element.text = line
    root_element.append(explanation_text_elem)
    
    if additional_link:
        if not (isinstance(additional_link, list) and isinstance(additional_link[0], str) and isinstance(additional_link[1], str)):
                print("Cannot print additional link. Wrong type. Please provide a list of 2 srings.")
        else:        
            link_y_pos = text_y_firstline + (num_lines-1)*line_spacing_px
            
            a_element = ET.Element(
                f"{{{SVG_NAMESPACE_URI}}}a",
                attrib = {f"{{{XLINK_NAMESPACE_URI}}}href": additional_link[0], "target": "_blank"}
            )
            link_text_element = ET.SubElement(
                a_element,
                f"{{{SVG_NAMESPACE_URI}}}text",
                attrib = {
                    'x': text_x_coord,
                    'y': str(link_y_pos),
                    'font-size': str(font_size),
                    'fill': fill_color,
                    'font-family': 'Arial, sans-serif',
                    'stroke': 'none',
                    'stroke-width': '0'
                }
            )
            link_text_element.text = additional_link[1]
            root_element.append(a_element)
            print(f"Added additional link {additional_link}")
    return root_element

def embed_svg_in_html(xmlroot):
    """
    Embeds the svg code in a ridiculously tiny html code

    Parameters
    ----------
    xmlroot : xmlroot of the SVG 
        
    Returns
    -------
    html code including the SVG

    """        
    
    #unicode is necessary - otherwise you get a byte string which we do not want
    svg_xml_code = ET.tostring(xmlroot, encoding='unicode', xml_declaration=False)
    
    html_template = f"""<!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
    </head>
    <body>
        {svg_xml_code}
    </body>
    </html>
    """
    print(f"svg_xmlcode = {svg_xml_code}")
    return html_template
    
def main():
    ''' 
    main routine
    '''
    
    xmlroot, element_list = ReadSVG(filename)
    
    filename_toml = filename_woextension + ".toml"
    
    # creating a backup of the toml file
    if os.path.exists(filename_toml): # is there already a toml file?
        try:
            filename_backup = filename_woextension + "_old.toml"
            shutil.copy2(filename_toml, filename_backup )
            print(f"Backup for '{filename_toml}' created as '{filename_backup}'.")
        except Exception as e:
            print(f"Error with creating the safety copy: {e}")
    
    
    data2write = [{fieldnames[0]: element, fieldnames[1]: ""} for element in element_list] 
    
    data_fromtoml = read_toml_data(filename_toml)
    print(f"Read data from toml: {data_fromtoml}")
    data2write = merge_file_data(data_fromtoml, element_list)
    write_toml_data(filename_toml, data2write)
    print(data2write)
    # add the balloons and the links
    newxmlroot = modify_text_tags(xmlroot, data2write)
    exp_text = ["Move your mouse over the items"]
    add_link = ["https://github.com/andreas-techdev/cvmap", "Made by cvmap"]
    newxmlroot = add_explanation_text(newxmlroot, explanation_text=exp_text, additional_link=add_link)
    
    tree = ET.ElementTree(newxmlroot)
    #write tree to new svg
    filename_output = filename_woextension + "_with_balloons.svg"
    try:
        # Open the file for writing
        # xml_declaration=True adds the <?xml ...?> line
        tree.write(filename_output, encoding=encoding, xml_declaration=True)

        print(f"New SVG-file '{filename_output}' successfully written.")
    except Exception as e:
        print(f"Error writing SVG file '{filename_output}': {e}")
    
    html_code = embed_svg_in_html(newxmlroot)
    filename_html = filename_woextension+".html"
    try:
        with open(filename_html, "w", encoding=encoding) as f:
            f.write(html_code)
    except IOError as e:
        print(f"Error writing html-file: {e}")
        
if __name__ == "__main__":
    main()


