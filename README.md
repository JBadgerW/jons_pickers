Jon's File Picker and Object Picker Readme
==========================================

## Description

A very basic terminal-based file picker with two modes, multi-file
and single-file. It's behavior attempts to mimic both the bash
Tab autocomplete, but also the auto-filtering behavior I saw in 
the Fresh text editor.

## File Picker vs Object Picker

There are two different functions available: file_picker and 
object_picker. The first transverses a file system and allows you
to pick a file/files which it returns in a list.

The other one, object_picker, takes a list of objects and allows
you to sift through and pick one or more out and then passes these
objects back in a list.

## Usage

from jons_pickers import file_picker
from jons_pickers import object_picker

my_files = file_picker(
    start_dir="home/cwd/whatever", 
    multi=True/False,
    prompt="File: "
)

my_objects = object_picker(list_of_objects, multi=True)
