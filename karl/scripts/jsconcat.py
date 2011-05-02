# Copyright (C) 2008-2009 Open Society Institute
#               Thomas Moroz: tmoroz@sorosny.org
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License Version 2 as published
# by the Free Software Foundation.  You may not use, modify or distribute
# this program under any other version of the GNU General Public License.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
# 
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

""" Concatenate the javascript resources  """

import sys
import os
import karl.views
import itertools

def _concat_path(fname, *rnames):
    return os.path.join(os.path.dirname(fname), *rnames)

def module_path(mod, *rnames):
    return _concat_path(mod.__file__, *rnames)

def filesindir(dir, *filenames):
    return (os.path.join(dir, f) for f in filenames)

def main(argv=sys.argv):
    if len(argv) > 1:
        raise RuntimeError, 'jsconcat accepts no parameters.'
    static_dir = module_path(karl.views, 'static')

    #jquery_dir = os.path.join(static_dir, 'jquery')  
    jquery_dir = os.path.join(static_dir, 'bottlecap', 'sl')  

    #ui_dir = os.path.join(static_dir, 'jquery-ui', '1.8.2' , 'js')  
    ui_dir = os.path.join(static_dir, 'bottlecap', 'sl', 'min')  

    plugins_dir = os.path.join(static_dir, 'jquery-plugins')
    bgiframe_dir = os.path.join(static_dir, 'jquery-ui', 'bgiframe_2.1.1')
    grid_dir = os.path.join(static_dir, 'jquery-ui', 'grid', 'ui')
    autobox_dir = os.path.join(static_dir, 'jquery-ui', 'autobox2')
    karl_dir = static_dir
    multistatusbox_dir = os.path.join(static_dir, 'karl-plugins', 'karl-multistatusbox')
    captionedimage_dir = os.path.join(static_dir, 'karl-plugins', 'karl-captionedimage')
    slider_dir = os.path.join(static_dir, 'karl-plugins', 'karl-slider')
    buttonset_dir = os.path.join(static_dir, 'karl-plugins', 'karl-buttonset')
    tinymce_base_dir = os.path.join(static_dir, 'tinymce')
    tinymce_dir = os.path.join(tinymce_base_dir, '3.3.9.2')

    packed_dir = os.path.join(static_dir, 'packed')

    
    # Resources loaded on every page
    #
    karl_ui_js = os.path.join(packed_dir, 'karl-ui.js')
    f = file(karl_ui_js, 'w')
    for fname in itertools.chain(
            #filesindir(jquery_dir, 'jquery-1.4.2.min.js'),
            filesindir(jquery_dir, 'jquery-1.4.4.min.js'),
            
            filesindir(bgiframe_dir, 'jquery.bgiframe.js'),

            filesindir(ui_dir, 'jquery-ui-1.9m3.min.js'),

            filesindir(grid_dir, 'ui.grid.js', 'ui.gridmodel.js'),
            filesindir(autobox_dir, 'jquery.templating.js', 'jquery.ui.autobox.ext.js', 'jquery.ui.autobox.js'),
            filesindir(multistatusbox_dir, 'karl.multistatusbox.js'),
            filesindir(captionedimage_dir, 'karl.captionedimage.js'),
            filesindir(slider_dir, 'karl.slider.js'),
            filesindir(buttonset_dir, 'karl.buttonset.js'),
            filesindir(plugins_dir, 'DD_roundies.js'),
            filesindir(plugins_dir, 'jquery.scrollTo.js'),
            filesindir(plugins_dir, 'jquery.tools.js'),
            ):
        f.write(file(fname).read())
    f.close()
    print "Successfully produced resource", karl_ui_js


    # the tinymce resource
    tiny_mce_js = os.path.join(packed_dir, 'karl-tiny.js')
    f = file(tiny_mce_js, 'w')
    for fname in itertools.chain(
            filesindir(tinymce_base_dir, 'karl-tiny-wire.js'),
            filesindir(tinymce_dir, 'jquery.tinysafe.js'),
            filesindir(tinymce_dir, 'tiny_mce.js'),
            filesindir(tinymce_dir, 'langs/en.js'),
            filesindir(tinymce_dir, 'themes/advanced/editor_template.js'),
            filesindir(tinymce_dir, 'themes/advanced/langs/en.js'),
            filesindir(tinymce_dir, 'plugins/paste/editor_plugin.js'),
            # XXX Starting with tinymce 3.2.4.1, the concatenated source
            # fails on IE7.
            ##filesindir(tinymce_dir, 'plugins/wicked/editor_plugin.js'),
            filesindir(tinymce_dir, 'plugins/wicked/editor_plugin_src.js'),
            filesindir(tinymce_dir, 'plugins/wicked/langs/en.js'),
            filesindir(tinymce_dir, 'plugins/spellchecker/editor_plugin.js'),
            filesindir(tinymce_dir, 'plugins/embedmedia/editor_plugin_src.js'),
            filesindir(tinymce_dir, 'plugins/imagedrawer/ajaxfileupload.js'),
            filesindir(tinymce_dir, 'plugins/imagedrawer/editor_plugin_src.js'),
            filesindir(tinymce_dir, 'plugins/imagedrawer/langs/en.js'),

            filesindir(tinymce_dir, 'plugins/kaltura/js/swfobject.js'),
            filesindir(tinymce_dir, 'plugins/kaltura/js/kaltura.min.js'),
            filesindir(tinymce_dir, 'plugins/kaltura/editor_plugin_src.js'),
            filesindir(tinymce_dir, 'plugins/kaltura/langs/en.js'),
            ):
        f.write(file(fname).read())
    f.close()
    print "Successfully produced resource", tiny_mce_js

if __name__ == '__main__':
    main()
