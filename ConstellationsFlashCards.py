# Constellations Flash-Cards
#
# TODO: Add a "clear results" button to the "results" toolbar.
#
# Copyright (c) 2010 by David A. Wallace
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#
# CITATIONS:
#
#   Bright Star Catalog
#     http://heasarc.gsfc.nasa.gov/W3Browse/star-catalog/bsc5p.html
#
#   Constellation figures -- derived from charts at
#     http://www.astro.wisc.edu/~dolan/constellations/
#     and the coordinates of the stars that the line-segments interconnect.
#
#  ACKNOWLEDGEMENTS
#
#  The author wishes to thank the following people for assistance with this project:
#
#    Daniel Castilo and Oscar Mendez Laesprella for encouragement, suggestions, bug
#    reports, beta testing and Spanish translation.  Thanks, guys -- I couldn't have
#    done this without you.
#
#    The owner and staff of The Java Room in Chelmsford, Massachusetts for the coffee,
#    wi-fi access and especially the live music.  Best environment I've ever had for
#    developing code in!
#
#    The members and officers of the Amateur Telescope Makers of Boston who encouraged
#    and educated me when I first discovered the wonder that is our planet's night sky.
#
# -------------------------------------------------------------------------------
#
# INDEX
#
# (Line numbers given below are approximate, within 5 lines, usually.)
#
#   Line No.    Content
#   --------    --------------------------------------
#      140      Version and date displayed by "About" function.
#      170      Start of the code -- trig algorithms
#      185      Definition for the ChartDisplay (main GUI) class
#                200  Area_Expose callback (screen refresh)
#                225  Event callback for controls
#                285  convert (ra,dec) to (x,y)
#                330  Code to plot the constellation figure:
#                      340  The outline and field
#		       385  Plot the map
#                      405  Plot the stars for a particular constellation
#                      425  Plot a Constellation figure
#                      450  Draw symbol of Star
#                      460  Choose a constellation ID
#                      480  Determine size of constellation
#                620  Fill the "names" combobox
#                660  Erase the screen
#      675      Definition for the ConstellationsFlashCards Activity class
#                685  Define the dictionary of constellation names and the array of
#                     constellation IDs
#                695  Establish the toolbars
#      780      Read configuration file and metadata
#      820      Write configuration file and metadata
#      840      Update configuration file
#


# =================================== IMPORTS ===================================

import pygtk
pygtk.require('2.0')
import gtk
import sys
import os
import gobject
from math import sin, cos, tan, asin, acos, atan, pi, sqrt, atan2
import random
from sugar.activity import activity
from sugar.activity.activity import get_bundle_path
import logging
from gettext import gettext


# Defensive method of gettext use: does not fail if the string is not translated.
def _(s):
  istrsTest = {}
  for i in range (0,4):
    istrsTest[str(i)] = str(i)

  try:
    i = gettext(s)
  except:
    i = s
  return i


# -------------------------------------------------------------------------------

# The bright star catalog is imported from stars1.py.
import stars1
star_chart = stars1.data


# The constellations figures have their own catalog.  This catalog could potentially be
# replaced by locale-specific figures, but that will break much of the code relating to
# object locating and identifying, since the program wants to use the 88 IAU constellation
# names (or at least their abbreviations).
import constellations
figures = constellations.data


# -------------------------------------------------------------------------------
#
# controls on second menubar ("Quiz"):
labelq1 = gtk.Label(_("Name"))
cbq1 = gtk.combo_box_new_text()
buttonq1 = gtk.Button(_("Tell me"))
buttonq2 = gtk.Button(_("Another"))
# controls on third menubar ("Results"):
containerr1 = gtk.VBox()
labelr1 = gtk.Label(_(" constellations seen."))
labelr2 = gtk.Label(" ")
labelr3 = gtk.Label(_(" correct on first try."))
labelr4 = gtk.Label(_(" correct on second try."))
# controls on last menubar ("About"):
containera1 = gtk.VBox()
labela1 = gtk.Label(_("Version 1.0 (build 10) of 2010.05.19.1500 UT"))
labela2 = gtk.Label(" ")
labela3 = gtk.Label(_("See http://wiki.laptop.org/go/ConstellationsFlashCards for help."))
labela4 = gtk.Label(" ")

name_from_abbrev = {}
constellations = []
#
# The program will bias the choice of constellation such that constellations with multiple
# correct asnswers are chosen less frequently.  The user gets five points for success on
# the first try, three points for success on the second try, one point for success on the
# third try and no points for needing 4 or more tries.  If a constellation has more than
# 50 points, we always skip it.  If it has 26 to 50 points, we skip it 4 out of 5 times,
# if it has 11 to 25 points, we skip it every other time.  We do not skip constellations
# which have 10 points or less.  These two arrays are needed to manage this capability:
#
# We save the constellation scores whenever a correct answer is given so that they persist
# between sessions.  We also count sessions by updating an entry in the scores file. When
# a session starts, we multiply the point score for each constellation by 0.8 as it is
# read in.
#
score = {}
seen = []
session_count = 1
quiz_count = 1
correct_first_count = 0
correct_second_count =  0

# ============================== START OF CODE ==================================

# Because Python's trig is done in radians and I often need answers in degrees,
# these two functions are provided to convert between radians and degrees.

def dtor(a):
  return a * pi / 180.0


def rtod(r):
  return r * 180.0 / pi



# ============================== ChartDisplay Object ============================

class ChartDisplay(gtk.DrawingArea):
  def __init__(self, context):
    super(ChartDisplay, self).__init__()
    self.context = context
    self.colors = {}
    self.canplot = False
    self.pangolayout = self.create_pango_layout("")
    self.add_events(gtk.gdk.BUTTON_PRESS_MASK | gtk.gdk.BUTTON1_MOTION_MASK |
	gtk.gdk.BUTTON2_MOTION_MASK)
    self.id = ""
    self.cname = ""
    self.points = 5
    self.cnumber = 0
    random.seed()


  def area_expose_cb(self, area, event):

# Determine the area we can draw upon and adjust the chart accordingly.

    rect = self.get_allocation()
    self.screensize = (rect.width, rect.height)
    self.margin = 40
    self.diameter = min(self.screensize[0], self.screensize[1]) - \
                    2 * self.margin
    self.xoffset = (self.screensize[0] - self.diameter) / 2 - self.margin
    self.yoffset = (self.screensize[1] - self.diameter) / 2 - self.margin

# Establish color selections (need only do this once).

    if (len(self.colors) == 0):
      self.gc = self.style.fg_gc[gtk.STATE_NORMAL]
      self.colormap = self.gc.get_colormap()
      self.colors[0] = self.colormap.alloc_color('white')
      self.colors[1] = self.colormap.alloc_color('black')
      self.colors[2] = self.colormap.alloc_color('red')
      self.colors[3] = self.colormap.alloc_color('gray')
      self.colors[4] = self.colormap.alloc_color('green')
      self.canplot = True
      self.plotchart(True)
    else:
      self.plotchart(False)


  def callback(self, widget, data=None):
    global score
    global seen
    global quiz_count
    global correct_first_count
    global correct_second_count

# Control callbacks are handled here.

    if (data == None):
      pass
    elif (data == "tell_me"):
      self.context.identifyobject.set_label(_("This constellation is named ") + \
                                            self.cname)
      labelr1.set_label(str(quiz_count) + _(" constellations seen."))
      labelr3.set_label(str(correct_first_count) +  _(" correct on first try."))
      labelr4.set_label(str(correct_second_count) + _(" correct on second try."))
      cbq1.set_sensitive(False)
      buttonq1.set_sensitive(False)
    elif (data == "another"):
      self.context.identifyobject.set_label("")
      cbq1.set_sensitive(True)
      buttonq1.set_sensitive(True)
      quiz_count = quiz_count + 1
      labelr1.set_label(str(quiz_count) + _(" constellations seen."))
      labelr3.set_label(str(correct_first_count) +  _(" correct on first try."))
      labelr4.set_label(str(correct_second_count) + _(" correct on second try."))
      self.plotchart(True)
    elif (data == "select_name"):
      if (cbq1.get_active() >= 0):
        name = cbq1.get_active_text()
        if (name == self.cname):
          self.context.identifyobject.set_label(_("That is correct."))
          id = self.id
          score[id] = score[id] + self.points
          if (self.points == 5):
            correct_first_count = correct_first_count + 1
          elif (self.points == 3):
            correct_second_count = correct_second_count + 1
          self.context.update_config(self.context.datafile)
          self.points = 5
          cbq1.set_sensitive(False)
          buttonq1.set_sensitive(False)
        else:
          self.context.identifyobject.set_label(_("Sorry, that is not the correct name."))
          self.points = self.points - 2
          if (self.points < 0):
            self.points = 0
      labelr1.set_label(str(quiz_count) + _(" constellations seen."))
      labelr3.set_label(str(correct_first_count) +  _(" correct on first try."))
      labelr4.set_label(str(correct_second_count) + _(" correct on second try."))
    else:
      pass
    return False


# Convert equatorial coordinates to pixel position(x, y) in normalized form on a square
# of self.diameter pixels.  RA is in hours; dec is in degrees.

  def radectoxy(self, polar):
    ra0 = self.rac * 15.0
    dec0 = self.decc
    ra = polar[0]
    dec = polar[1]
    ra = ra * 15

# If self.size is negative, this is a circumpolar constellation and is plotted on a circle
# where 00h is down in the northern sky and up in the southern sky and the radius is
# abs(size).  Otherwise, the constellation is plotted in a square whose center is
# (self.rac, self.decc) and whose size is self.size

    if (self.size < 0.0):
      if (dec0 > 0):
        r = (dec0 - dec) / -self.size * (self.diameter / 2.0)
        theta =  360.0 - ra
        y = 0.9 * r * cos(dtor(theta))
      else:
        r = (dec0 - dec) / -self.size * (self.diameter / 2.0)
        theta = 180.0 - ra
        y = -0.9 * r * cos(dtor(theta))
      x = 0.9 * r * sin(dtor(theta))
    else:

# Center the constellation and magnify to fit the chart.

      dec = dec0 - dec
      ra = ra0 - ra
      if (ra < -180.0):
        ra = ra + 360.0
      if (ra > 180.0):
        ra = ra - 360.0
      dec = dtor(dec)
      ra = dtor(ra)
      x = self.diameter / 2.0 * ra / pi
      y =  self.diameter * dec / pi
      x = 0.9 * x * 360.0 / self.size
      y = 0.9 * y * 180.0 / self.size
    return (x, y)

 
# -------------------------------------------------------------------------------
#
#   Methods for drawing the chart:

  def plotchart(self, newplot):
    if (self.canplot):
      self.plot_field()
      self.plot_sky(newplot)
    return True


  def plot_field(self):

# Erase prior plot

    if (not self.canplot):
      return
    self.cleararea()
    self.gc.set_foreground(self.colors[0])
    self.window.draw_rectangle(self.gc,
                              True,
                              self.xoffset + self.margin - 2,
                              self.yoffset + self.margin - 2,
                              self.diameter + 4,
                              self.diameter + 4)

# Plot sky square

    self.gc.set_foreground(self.colors[1])
    self.window.draw_rectangle(self.gc,
                              False,
                              self.xoffset + self.margin - 2,
                              self.yoffset + self.margin - 2,
                              self.diameter + 4,
                              self.diameter + 4)

# label the cardinal points.

    self.gc.set_foreground(self.colors[1])
    self.pangolayout.set_text(_("N"))
    self.window.draw_layout(self.gc,
                     self.xoffset + self.margin + self.diameter / 2 - 10,
                     self.margin - 30, self.pangolayout)
    self.pangolayout.set_text(_("S"))
    self.window.draw_layout(self.gc,
                     self.xoffset + self.margin + self.diameter / 2 - 10,
                     2 * self.margin + self.diameter - 30, self.pangolayout)
    self.pangolayout.set_text(_("E"))
    self.window.draw_layout(self.gc,
                     self.xoffset + self.margin - 30,
                     self.margin + self.diameter / 2 - 10, self.pangolayout)
    self.pangolayout.set_text(_("W"))
    self.window.draw_layout(self.gc,
                     self.xoffset + self.margin + self.diameter + 10,
                     self.margin + self.diameter / 2 - 10, self.pangolayout)
    self.gc.set_foreground(self.colors[1])
    return True


  def plot_sky(self, choose):
    if (choose):
      self.cnumber = random.randrange(len(constellations))
      self.id = self.pick_constellation()
      self.cname = name_from_abbrev[self.id]
    (self.rac, self.decc, self.size) = self.constellation_size(self.id)
#    self.context.identifyobject.set_label("rac=" + str(self.rac) +\
#                                            " decc=" + str(self.decc) +\
#                                            " size=" + str(self.size) )
    self.plot_stars(self.id)
    self.plot_constellation(self.id)
    self.gc.set_foreground(self.colors[1])
    if (choose):
      self.fill_names_combobox()


  def plot_stars(self, id):
      
# Plot the stars.
# FIXME: Some stars are in more than one constellation.  We need to make a special version
# of the star catalog with duplicate entries for those cases.  (E.g.: Auriga / Taurus and
# Andromeda / Pegasus.)

    for name, (ra, dec, mag, cid) in star_chart.iteritems():
      if (cid == id):

# convert the ra and dec to pixel coordinates x and y

        (px, py) = self.radectoxy((ra, dec))
        px = px + self.diameter / 2.0
        py = py + self.diameter / 2.0
        starsize = 4 + 2 * int(7.0 - mag)
        px = px + self.margin - 2 + self.xoffset - starsize / 2
        py = py + self.margin - 2 + self.yoffset - starsize / 2
        if (mag <= 6.0):
          self.plot_star(px, py, starsize)


  def plot_constellation(self, id):

# Plot the constellation figures.  This is essentially the same process as for
# plotting a star but we have to figure out the alt/az coordinates for both ends
# of the line segment.

    self.gc.set_foreground(self.colors[1])
    for code, (name, lines) in figures.iteritems():
      if (code == id):
        for i in range(len(lines)):
          (ra1, dec1, ra2, dec2) = lines[i]
          (px1, py1) = self.radectoxy((ra1, dec1))
          px1 = px1 + self.diameter / 2.0
          py1 = py1 + self.diameter / 2.0
          px1 = px1 + self.margin - 2 + self.xoffset
          py1 = py1 + self.margin - 2 + self.yoffset
          (px2, py2) = self.radectoxy((ra2, dec2))
          px2 = px2 + self.diameter / 2.0
          py2 = py2 + self.diameter / 2.0
          px2 = px2 + self.margin - 2 + self.xoffset
          py2 = py2 + self.margin - 2 + self.yoffset
          self.window.draw_line(self.gc, px1, py1, px2, py2)


  def plot_star(self, px, py, starsize):
    self.window.draw_arc(self.gc, True,
             px,
             py,
             starsize,
             starsize,
             0,
             360*64)


  def pick_constellation(self):
    global seen

# Using a random number between 0 and 87, select a constellation ID.

    id = -1
    while (id < 0):
      id = constellations[self.cnumber]
      if (score[id] > 50):
        id = -1 # always skip if score > 50
      elif (score[id] > 25) and (seen[self.cnumber] > 1):
        seen[self.cnumber] = seen[self.cnumber] - 1
        id = -1 # skip 80% of the time if score between 26 and 50
      elif (score[id] > 10) and (seen[self.cnumber] > 4):
        seen[self.cnumber] = seen[self.cnumber] - 1
        id = -1 # skip 50% of the time if score between 11 and 25
      else: # never skip
        pass
    seen[self.cnumber] = 5
    return id


  def constellation_size(self, id):
    rac = 12.0
    decc = 0.0
    size = 360.0
    ramin = 24.0
    ramax = 0.0
    decmin = 90.0
    decmax = -90.0

#  Since most constellations are plotted on a cylinder, we can determine their center
#  point and size simply by getting the coordinates of every star in the constellation
#  and determining the bounding rectangle.  Then we return the center (ra, dec) and the
#  size (in ddegrees) of the square which would contain the constellation.  In the case
#  where the constellation spans the ra = 00h meridian, we compensate for wrap-around
#  by adding 12h to every ra value and then subtracting 12h from the ra of the center
#  point.
#
#  But some constellations are close to the celestial pole and a cylindrical projection
#  doesn't work.  For these, we return the pole coordinate as the center, the minimum
#  (maximum for the south pole) declanation as the size but negative so that radectoxy()
#  knows that the projection is polar.  For the purposes of this program, the circumpolar
#  constellations are defined as those whose decc is over 60 (or under -60) degrees.
#  These are:
#  Dra
#  Umi
#  Oct
#  Pav
#  Aps
#  Ara
#  Tra
#  Cha
#  Men
#  Hyi
#  Tuc

    for name, (ra, dec, mag, cid) in star_chart.iteritems():
      if (cid == id):

#  FIXME: The assumption is that the stick figure contains no line whose end-point is
#  not already specified by a star's coordinates.  It would be better to also enumerate
#  the stick-figure's endpoints when determining the constellation's boundaries.

        if (ra < ramin):
          ramin = ra
        elif (ra > ramax):
          ramax = ra
        if (dec < decmin):
          decmin = dec
        elif (dec > decmax):
          decmax = dec
    if not (
           (id == "Aps") or 
            (id == "Ara") or 
            (id == "Cha") or 
            (id == "Dra") or 
            (id == "Hyi") or 
            (id == "Men") or 
            (id == "Oct") or 
            (id == "Pav") or 
            (id == "Tra") or 
            (id == "Tuc") or 
            (id == "Umi")):
      if (ramin <= 1.0) and (ramax >= 23.0):

# This constellation spans the ra = 00h meridian.

        ramin = 24.0
        ramax = 0.0
        for name, (ra, dec, mag, cid) in star_chart.iteritems():
          if (cid == id):
            ra = ra + 12.0
            if (ra >= 24.0):
              ra =  ra - 24.0
            if (ra < ramin):
              ramin = ra
            elif (ra > ramax):
              ramax = ra
        rac = (ramin + ramax) / 2.0 - 12.0
        if (rac < 0.0):
          rac = rac + 24.0
      else:
        rac = (ramin + ramax) / 2.0
      dra = ramax - ramin
      dra = dra * 15.0
      decc = (decmin + decmax) / 2.0
      ddec = decmax - decmin
      if (dra > ddec):
        size = dra
      else:
        size = ddec

# Round off the size to the next higher multiple of 5 degrees.

      size = int(size / 5.0) + 1
      size = size * 5.0

# Ensure that size is at least 30 degrees.

      if (size < 30.0):
        size = 30.0
      return (rac, decc, size)

# Handle the circumpolar constellations.

    elif (
          (id == "Aps") or
          (id == "Ara") or
          (id == "Cha") or
          (id == "Hyi") or 
          (id == "Men") or 
          (id == "Pav") or 
          (id == "Oct") or
          (id == "Tra") or 
          (id == "Tuc")):

# Round off the size to the next higher multiple of 5 degrees.

      size = 90.0 + decmax
      size = int(size / 5.0) + 1
      size = size * 5.0
      return (0, -90, -size)
    elif (
#          (id == "Cam") or
#          (id == "Cep") or
          (id == "Dra") or
          (id == "Umi")):

# Round off the size to the next higher multiple of 5 degrees.

      size = 90.0 - decmin
      size = int(size / 5.0) + 1
      size = size * 5.0
      return (0, 90, -size)


  def fill_names_combobox(self):

# Create a list of five names, initialized to ""

    names = ["", "", "", "", ""]
    numbers = [-1, -1, -1, -1, -1]
    for i in range(5):
      try:
        cbq1.remove_text(4 - i)
      except:
        pass

# Now set one of these names to self.cname.

    k = random.randrange(5)
    names[k] = self.cname
    numbers[k] = self.cnumber
      
# Choose four additional constellation names (by random choice).  Add these names to the
# list, being sure not to overwrite any non-blank value or use the same name twice.

    i = 0
    while (i < 4):
      r = random.randrange(len(constellations))
      if not (r in numbers):
        id = constellations[r]
        cname = name_from_abbrev[id]
        for j in range(5):
          if (names[j] == ""):
            names[j] = cname
            numbers[j] = r
            i = i + 1
            break
      
# Fill cbq1 with the five strings.

    for i in range(5):
      cbq1.append_text(names[i])


  def cleararea(self):
    
# Clear the drawing surface

    self.gc.set_foreground(self.colors[3])
    self.window.draw_rectangle(self.gc,
                                    True,
                                    1,
                                    1,
                                    self.screensize[0],
                                    self.screensize[1])


# ========================= ConstellationsFlashCards Object ==========================

class ConstellationsFlashCards(activity.Activity):
  def __init__(self, handle):
    global name_from_abbrev
    global constellations
    global score
    global seen
    activity.Activity.__init__(self, handle)
    self.datafile = os.path.join(activity.get_activity_root(),\
                                 "data", "C_FC.cfg")
      
# Build the translation from constellation name to constellation ID (needed so we can
# have a list of names to choose from).  At the same time, make an array of constellation
# IDs so the randomizer can pick one.

    for id in sorted(figures.keys()):
      (name, lines) = figures[id]
      name_from_abbrev[id] = name
      constellations.append(id)
      score[id] = 0
      seen.append(5)

# Create toolbox
      
    toolbox = activity.ActivityToolbox(self)
    self.set_toolbox(toolbox)
    self.quiz_toolbar = gtk.Toolbar()
    self.quiz_toolbar.add(labelq1)
    self.quiz_toolbar.add(cbq1)
    self.quiz_toolbar.add(buttonq1)
    self.quiz_toolbar.add(buttonq2)

    self.result_toolbar = gtk.Toolbar()
    containerr1.add(labelr1)
    containerr1.add(labelr2)
    containerr1.add(labelr3)
    containerr1.add(labelr4)
    self.result_toolbar.add(containerr1)

    self.about_toolbar = gtk.Toolbar()
    containera1.add(labela1)
    containera1.add(labela2)
    containera1.add(labela3)
    containera1.add(labela4)
    self.about_toolbar.add(containera1)
 
# Fill the toolbox bars

    toolbox.add_toolbar(_("Quiz"), self.quiz_toolbar)
    toolbox.add_toolbar(_("Results"), self.result_toolbar)
    toolbox.add_toolbar(_("About"), self.about_toolbar)

# Create the GUI objects.

    scrolled = gtk.ScrolledWindow()
    scrolled.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
    scrolled.props.shadow_type = gtk.SHADOW_NONE
    self.chart = ChartDisplay(self)
    eb = gtk.EventBox()
    vbox = gtk.VBox(False)
    self.identifyobject = gtk.Label("")
    vbox.pack_start(self.identifyobject, expand=False)
    vbox.pack_start(self.chart)
    eb.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("gray"))

# Stack the GUI objects.

    scrolled.add_with_viewport(vbox)

# Connect the event handlers

    self.chart.connect("expose_event", self.chart.area_expose_cb)
    buttonq1.connect("clicked", self.chart.callback, "tell_me")
    buttonq2.connect("clicked", self.chart.callback, "another")
    cbq1.connect("changed", self.chart.callback, "select_name")
    cbq1.set_sensitive(True)
    buttonq1.set_sensitive(True)

# Set the canvas

    self.set_canvas(scrolled)

# Show the GUI stack.

    toolbox.show()
    toolbox.set_current_toolbar(1)
    self.chart.show()
    eb.show()
    scrolled.show()
    self.show_all()

# FIXME: We can't do sharing yet, so hide the control for it.

    toolbar = toolbox.get_activity_toolbar()
    toolbar.share.hide()

# If C_FC.cfg exists, get the previous scores.

    self.read_file(self.datafile)
    labelr1.set_label(str(quiz_count) + _(" constellations seen."))
    labelr3.set_label(str(correct_first_count) +  _(" correct on first try."))
    labelr4.set_label(str(correct_second_count) + _(" correct on second try."))

# Establish initial state of controls and do a plot.

    self.chart.plotchart(True)


  def read_file(self, filename=""):
    global score
    global quiz_count
    global correct_first_count
    global correct_second_count
    global session_count
# Read the values for the scores of all constellations.
# We presently have no metadata to read.
    if (filename == ""):
      self.identifyobject.set_label("Read_file: no filename given.")
      return
    try:
      f = open(filename, "r")
    except:
      return
    try:
      for old_data in f:

# Each line of interest consists of the three-character constellation ID, a colon and
# an integer score.  If the colon isn't present as character #4, see if the line is one
# of the special-case directives like "seen:", "sessions:", "learned:" or "familiar:".

        if (old_data[3] == ':'):
          id = old_data[:3]
          points = int(old_data[4:])
          score[id] = int(points * 0.8)
        elif (old_data[:5] == "seen:"):
          quiz_count = int(old_data[5:]) + 1
        elif (old_data[:8] == "learned:"):
          correct_first_count = int(old_data[8:])
        elif (old_data[:9] == "familiar:"):
          correct_second_count = int(old_data[9:])
        elif (old_data[:9] == "sessions:"):
          session_count = int(old_data[9:]) + 1
        else:
          pass
    except:
      pass
    f.close()

    
  def write_file(self, filename=""):
# Write the values for the scores of all constellations.

# Note: currently not used!

    if (filename == ""):
      self.identifyobject.set_label("Write_file: no filename given.")
      return
    f = open(filename, "w")
    f.truncate(0)
    for i in range(len(constellations)):
      id = constellations[i]
      points = score[id]
      f.write(id + ":" + str(points) + '\n')
    f.write("sessions:" + str(session_count) + '\n')
    f.write("seen:" + str(quiz_count) + '\n')
    f.write("learned:" + str(correct_first_count) + '\n')
    f.write("familiar:" + str(correct_second_count) + '\n')
    f.close()
# We presently have no metadata to write.


  def update_config(self, filename=""):
# Modify the values for the scores of all constellations.
    if (filename == ""):
      self.identifyobject.set_label("Update_config: no filename given.")
      return
    data = []
    try:
      f = open(filename, "r")
    except:
      f = open(filename, "w")
    else:
      try:
        for old_data in f:

# Each line of interest consists of the three-character constellation ID, a colon and
# an integer score.  If the colon isn't present as character #4, see if the line is one
# of the special-case directives like "sessions:", "learned:" or "familiar:".

          if (old_data[3] == ':'):
            pass
          elif (old_data[:8] == "learned:"):
            pass
          elif (old_data[:9] == "familiar:"):
            pass
          elif (old_data[:9] == "sessions:"):
            pass
          else:
            data.append(old_data)
      except:
        pass
      f.close()
      f = open(filename, "w")

# Write all the non-conforming lines.

      for i in range(len(data)):
        f.write(data[i])

# Write the session count and results.

    f.write("sessions:" + str(session_count) + '\n')
    f.write("seen:" + str(quiz_count) + '\n')
    f.write("learned:" + str(correct_first_count) + '\n')
    f.write("familiar:" + str(correct_second_count) + '\n')

# Now write the scores.

    for i in range(len(constellations)):
      id = constellations[i]
      points = score[id]
      f.write(id + ':' + str(points) + '\n')
    f.close()
