# !/usr/bin/python
# -*- coding: utf-8 -*-

import ctypes
import ctypes.util
import os
import os.path
import sys
from ctypes import windll, sizeof, c_ushort, c_char
import time
import cv2
import numpy as np
from colorama import Fore

def _load_library():
    """
    Loads the xclibw64.dll shared library.
    """
    if (os.name != 'nt'):
        raise Exception("Your operating system is not supported. " \
                        "YPLs' OWL-640-T API only works on Windows.")
    lib = None
    filename = ctypes.util.find_library("xclibw64")
    if (filename is not None):
        lib = ctypes.windll.LoadLibrary(filename)
    else:
        filename = "lib/xclibw64.dll"
        lib = ctypes.windll.LoadLibrary(filename)
        if (lib is None):
            filename = "%s/lib/xclibw64.dll" % os.path.dirname(sys.argv[0])
            lib = ctypes.windll.LoadLibrary(lib)
            if (lib is None):
                raise Exception("Could not find shared library xclibw64.dll.")
    return lib

class CameraError(Exception):
    def __init__(self, mesg):
        self.mesg = mesg

    def __str__(self):
        return self.mesg

class Camera(object):
    def __init__(self):
        self.pixci_opened = False
        self.bit_depth = None
        self.roi_shape = None
        self.camera = None
        self.exposure = None
        self.roi_pos = None
        self.frametime = None
        self.epix = windll.LoadLibrary("lib/xclibw64.dll")

    def get_Err(self, Error_Code=None):
        char_buf = (c_char * 2000)()
        c_buf_size = sizeof(char_buf)
        self.epix.pxd_mesgErrorCode2(Error_Code, char_buf, c_buf_size)
        print(Fore.LIGHTRED_EX + char_buf.value.decode("utf-8"))

    def open(self):
        if self.pixci_opened:
            self.close()
        formatfile = r"C:/Users/sar247/OneDrive - University of Pittsburgh/#PHOTONICS LAB#/#PROJECTS#/Components/# Test Equipment/lib/OWL640T_Video_Setup_Format.fmt"
        i = self.epix.pxd_PIXCIopen("", "", formatfile.encode("utf-8"))
        if i == 0:
            print(Fore.GREEN + "Frame grabber opened successfully.")
            self.pixci_opened = True
        else:
            self.get_Err(i)
            self.epix.pxd_mesgFault()
            raise CameraError(Fore.LIGHTRED_EX + "Opening the frame grabber failed with error code " + str(i))

        xdim = self.get_xdim()
        ydim = self.get_ydim()
        num_fields = self.get_idim()
        AR = self.get_aspect_ratio()
        bit_depth = self.get_bit_depth()
        num_units = self.get_num_units()
        num_buffers = self.get_num_buffers()

        print(Fore.LIGHTBLACK_EX + "///////////////////////////////////////////////////////////")
        print(Fore.YELLOW + "Number of units: " + str(num_units) + ", Number of buffers: " + str(
            num_buffers) + ",  Number of video fields: " + str(num_fields))
        print(Fore.YELLOW + "Xdim: " + str(xdim) + ", Ydim: " + str(ydim) + ", Bit Depth: " + str(
            bit_depth) + ",  Aspect Ratio: " + str(AR))
        print(Fore.LIGHTBLACK_EX + "///////////////////////////////////////////////////////////\n")

    def close(self):
        print(Fore.LIGHTBLACK_EX + "\n///////////////////////////////////////////////////////////")
        i = self.epix.pxd_PIXCIclose("", "", "")
        if i == 0:
            print(Fore.GREEN + "Frame grabber closed successfully.")
        else:
            self.get_Err(i)
            self.epix.pxd_mesgFault()
            raise CameraError(Fore.LIGHTRED_EX + "Closing the frame grabber failed with error code " + str(i))

    def get_xdim(self):
        return self.epix.pxd_imageXdim()

    def get_ydim(self):
        return self.epix.pxd_imageYdim()

    def get_idim(self):
        return self.epix.pxd_imageIdim()

    def get_aspect_ratio(self):
        return self.epix.pxd_imageAspectRatio()

    def get_bit_depth(self):
        return self.epix.pxd_imageBdim()

    def get_num_units(self):
        return self.epix.pxd_infoUnits()

    def get_num_buffers(self):
        return self.epix.pxd_imageZdim()

    def start_live_capture(self, unitmap=0x1, framebuf=None):
        if framebuf is None:
            framebuf = self.get_frame_number(unitmap)
        live = self.epix.pxd_goLive(unitmap, framebuf)
        if live == 0:
            print(Fore.LIGHTCYAN_EX + "live now")
        else:
            print(
                Fore.LIGHTRED_EX + "The library is not open for use Or Video is already being captured and must be terminated before initiating a new capture.")
            self.get_Err(live)

    def stop_live_capture(self, unitmap=0x1):
        Unlive = self.epix.pxd_goUnLive(unitmap)
        if Unlive == 0:
            print(Fore.LIGHTCYAN_EX + "Unlive now")
        else:
            print(Fore.LIGHTRED_EX + "The library is not open for use Or some other error occurred.")
            self.get_Err(Unlive)

    def gone_live(self, unitmap=0x1, rsvd=0):
        status = self.epix.pxd_goneLive(unitmap, rsvd)
        if status == 0:
            self.epix.pxd_mesgFault()
            print(Fore.LIGHTBLUE_EX + "Unit " + str(unitmap) + " in Frame Grabber, is not in use.")
            return False
        else:
            print(Fore.LIGHTCYAN_EX + "Unit " + str(unitmap) + " in Frame Grabber is in use.")
            self.get_Err(status)
            return True

    def snap(self, unitmap=0x1, framebuf=None):
        if framebuf is None:
            framebuf = self.get_frame_number(unitmap)
        snap_stat = self.epix.pxd_doSnap(unitmap, framebuf, 10000)
        self.epix.pxd_mesgFault()
        if snap_stat == 0:
            print(Fore.LIGHTBLUE_EX + "Snap Successful.")
        else:
            print(Fore.LIGHTRED_EX + "Error Occurred during snap.")
            self.get_Err(snap_stat)

    def start_continuous_capture(self, unitmap=0x1, startbuf=1, endbuf=None):
        if endbuf is None:
            endbuf = self.get_num_buffers()
        continuous = self.epix.pxd_goLiveSeq(unitmap, startbuf, endbuf, 1, 0, self.get_idim())
        if continuous == 0:
            print(Fore.LIGHTCYAN_EX + "Continuous capture started.")
        else:
            print(Fore.LIGHTRED_EX + "Error Occurred during continuous capture.")
            self.get_Err(continuous)

    def start_sequence_capture(self, unitmap=0x1, startbuf=1, endbuf=None, incbuf=1, n_frames=50, videoperiod=1):
        if endbuf is None:
            endbuf = self.get_num_buffers()
        sequence = self.epix.pxd_goLiveSeq(unitmap, startbuf, endbuf, incbuf, n_frames, videoperiod)
        if sequence == 0:
            print(Fore.LIGHTCYAN_EX + "Sequence captured.")
        else:
            print(Fore.LIGHTRED_EX + "Error Occurred during sequence capture.")
            self.get_Err(sequence)

    def get_image(self, unitmap=0x1, framebuf=None):
        if framebuf is None:
            framebuf = self.get_frame_number(unitmap)
        xdim = self.get_xdim()
        ydim = self.get_ydim()
        bit_depth = self.get_bit_depth()
        imagesize = xdim * ydim
        c_buf = (c_ushort * imagesize)()
        c_buf_size = sizeof(c_buf)
        color = "Grey"
        stat_read = self.epix.pxd_readushort(unitmap, framebuf, 0, 0, -1, -1, c_buf, c_buf_size, color.encode("utf-8"))
        if stat_read < 0:
            return self.get_Err(stat_read)
        else:
            im = np.frombuffer(c_buf, dtype=c_ushort, count=-1, offset=0)
            print(Fore.LIGHTBLACK_EX + "Image Read Successfully.")
            print(Fore.LIGHTBLACK_EX + "Frame Size: " + str(im.shape) + ", Minimum Pixel Intensity: " + str(
                np.min(im)) + ", Maximum Pixel Intensity: " + str(np.max(im)))
            im = im.reshape([ydim, xdim])
        if bit_depth > 8:
            diff_bit = 16 - bit_depth
            im = im << diff_bit
        return im

    def capture_All(self, unitmap=0x1, ulx=0, uly=0, lrx=-1, lry=-1):
        num_units = self.get_num_units()
        num_buffers = self.get_num_buffers()
        xdim = self.get_xdim()
        ydim = self.get_ydim()
        bit_depth = self.get_bit_depth()

        imagesize = xdim * ydim
        c_buf = (c_ushort * imagesize)()
        c_buf_size = sizeof(c_buf)
        c_buf_rgb = (c_ushort * (imagesize * 3))()
        c_buf_rgb_size = sizeof(c_buf_rgb)
        frames_grey = []
        frames_rgb = []
        for unit in range(1, num_units + 1):
            for buf in range(1, num_buffers + 1):
                color = "Grey"
                stat = self.epix.pxd_readushort(unitmap, buf, ulx, uly, lrx, lry, c_buf, c_buf_size,
                                                color.encode("utf-8"))
                if stat < 0:
                    return self.get_Err(stat)
                else:
                    im = np.frombuffer(c_buf, c_ushort).reshape([ydim, xdim])
                    print(Fore.LIGHTBLACK_EX + "Number of Copied Pixels: " + str(stat))
                    print(Fore.LIGHTBLACK_EX + "Unit: " + str(unit) + ", Buffer: " + str(buf) + ", Grey Value: " + str(
                        im[0]))
                if bit_depth > 8:
                    diff_bit = 16 - bit_depth
                    im = im << diff_bit
                frames_grey.append(im)
                color = "RGB"
                stat = self.epix.pxd_readushort(unitmap, buf, ulx, uly, lrx, lry, c_buf_rgb, c_buf_rgb_size,
                                                color.encode("utf-8"))
                if stat < 0:
                    return self.get_Err(stat)
                else:
                    im = np.frombuffer(c_buf, c_ushort).reshape([ydim, xdim])
                    print(Fore.LIGHTBLACK_EX + "Number of Copied Pixels: " + str(stat))
                    print(Fore.LIGHTBLACK_EX + "Unit: " + str(unit) + ", Buffer: " + str(buf) + ", RGB Value: " + str(
                        im[0]) + "/" + str(im[1]) + "/" + str(im[2]))
                if bit_depth > 8:
                    diff_bit = 16 - bit_depth
                    im = im << diff_bit
                frames_rgb.append(im)
        return frames_grey, frames_rgb

    def get_frame_number(self, unitmap=0x1):
        f_number = self.epix.pxd_capturedBuffer(unitmap)
        if f_number == 0:
            print(Fore.LIGHTRED_EX + "The library is not open for use or no frame has been captured.")
            return self.get_Err(f_number)
        else:
            print(Fore.LIGHTYELLOW_EX + "Most recent captured frame number: " + str(f_number))
        return f_number

    def save_Image(self, unitmap=0x1, framebuf=1, filename="test.tif", ulx=0, uly=0, lrx=-1, lry=-1):
        name = "Images/" + filename
        save_stat = self.epix.pxd_saveTiff(unitmap, name.encode("utf-8"), framebuf, ulx, uly, lrx, lry, 0, 0)
        self.epix.pxd_mesgFault()
        if save_stat == 0:
            print(Fore.LIGHTBLACK_EX + "Image Saved Successfully.")
        else:
            return self.get_Err(save_stat)

    def get_frame_rate(self, unitmap=0x1):
        FR = self.epix.pxd_SILICONVIDEO_getCtrlFrameRate(unitmap)
        if FR == 0:
            self.epix.pxd_mesgFault()
            print(Fore.LIGHTRED_EX + "The library is not open for use, or the wrong frame grabber is in use.")
        else:
            print(Fore.LIGHTYELLOW_EX + "Frame Rate: " + str(FR))
        return FR

    def save_buffer(self, filename, frames):
        buffer_save = self.epix.pxd_saveRawBuffers(0x1, filename.encode("utf-8"), frames[0], frames[1], 0, 0, 0, 0)
        return

    def load_buffer(self, filename, frames):
        buffer_load = self.epix.pxd_loadRawBuffers(0x1, filename.encode("utf-8"), frames[0], frames[1], 0, 0, 0, 0)
        return

if __name__ == '__main__':
    OWL_640_T = Camera()
    OWL_640_T.open()
    OWL_640_T.gone_live(0x1)
    # OWL_640_T.start_live_capture(0x1, 1)
    while True:
        framesrgb, framesgrey = OWL_640_T.capture_All()
        cv2.imshow('Frame', framesgrey)
        if cv2.waitKey(24) & 0XFF == 27:  # Press esc Button to stop the video ...
            break
    OWL_640_T.stop_live_capture(0x1)
    OWL_640_T.close()
