#!/usr/bin/python
import math
import struct
import sys

#shannon entropy of the data:
#calcs minimum # of bits needed to represent a byte
#so something out of 8
#which is then scaled to between 0, 1, with higher == greater entropy
#just here to try and guess if data in records might be compressed
def entropy(buf):

    bLen = len(buf)
    counts = {}
    for b in buf:
        counts.setdefault(b, 0)
        counts[b] += 1

    freqs = []
    for count in counts.values():
        freqs.append(float(count) / float(bLen))

    ent = 0.0
    for freq in freqs:
        ent = ent + freq * math.log(freq, 2)
    return -ent / 8

#stolen
#http://code.activestate.com/recipes/142812/
FILTER=''.join([(len(repr(chr(x)))==3) and chr(x) or '.' for x in range(256)])

def hexdump(src, length=16, indent=0, addr=0):
    N=addr; result=''
    while src:
       s,src = src[:length],src[length:]
       hexa = ' '.join(["%02X"%ord(x) for x in s])
       s = s.translate(FILTER)
       result += (" "*indent) + "%010X   %-*s   %s\n" % (N, length*3, hexa, s)
       N+=length
    return result

######

def readHeader(buf):

    offset = 0
    sig, version, fileSize, frameThing1, w1, w2, w3, hasKeyFrameOffset, \
    hasKeyFrameOffset2, frameCount, xHdrLen1, xHdrLen2 = struct.unpack("<4sLLLHHHHLLHH",
            buf[offset:offset+0x24])
    offset += 0x24

    print "Dumping WRF header.."
    print("--Sig %s, version %#x, fileSize %#x, frameThing1 %#x\n"
          "--hasKeyFrameOffset %#x, hasKeyFrameOffset2 %#x, frameCount %#x\n"
          "--xHdrLen1 %#x xHdrLen2 %#x" %
          (sig, version, fileSize, frameThing1, hasKeyFrameOffset,
              hasKeyFrameOffset2, frameCount, xHdrLen1, xHdrLen2))

    if version < 0x401:
        print "Old version, I don't know how to parse it"
        sys.exit(1)

    offset += xHdrLen1 + xHdrLen2
    if hasKeyFrameOffset2 != 0 or hasKeyFrameOffset != 0:
        #read key frame descriptor
        keyFrameOffset, unknown = struct.unpack("<LL", buf[offset:offset+8])
        print("\nDumping key frame descriptor\n"
              "--keyFrameOffset %#x, unknown %#x" % (keyFrameOffset, unknown))
        offset += 8
        keyFrameOffset += offset
    else:
        keyFrameOffset = offset

    return (offset, keyFrameOffset, version)

#
def readKeyFrame(buf, offset, version):
    kType, kTime, kSize, kUnknown = struct.unpack("<BLLB",
            buf[offset:offset+10])

    print("\nDumping key frame @ offset %#x\n"
          "--type %#x, time %#x, size %#x, unknown %#x" %
          (offset, kType, kTime, kSize, kUnknown))

    if version < 0x401:
        offset += 0x9
    else:
        offset += 0x24

    return offset

def dumpSubRecords(buf, fileOffset):
    end = len(buf)
    offset = 0
    while offset <= end - 3:
        rType, rLen = struct.unpack("<BH", buf[offset:offset+3])

        print("----Subrecord @ offset %#x, type %#x, len %#x" %
                (fileOffset + offset, rType, rLen))

        offset += 3
        rData = buf[offset:offset+rLen-3]
        if rLen > 0:
            print(hexdump(rData, length=16, indent=12))

        if rLen:
            offset += rLen - 3


def dumpRecords(buf, offset, version):

    end = len(buf)

    print "\nDumping records starting @ offset %#x.." % (offset)
    count = 0
    while offset <= end - 5:

        flagsAndLen, uk1, uk2, rLen = struct.unpack("<BBBH",
                buf[offset:offset+5])

        rType = flagsAndLen & 0xf
        rXlen = (flagsAndLen >> 4) << 0x10
        rTlen = rXlen + rLen
        data = buf[offset+5:offset+5+rTlen]

        print("--Record @ offset %#x: type %#x, xLen %#x, rLen %#x, totalLen %#x, uk1 %#x, uk2 %#x, entropy %f" %
                (offset, rType, rXlen, rLen, rTlen, uk1, uk2, entropy(data)))

        #handle record type
        if rType == 1 or rType == 3 or rType == 9:
            #assume it has subrecords if there is enough data
            if rTlen >= 5:
                first4 = (struct.unpack("L", data[0:4]))[0]
                print "First4 %#x" % first4
                if first4 == 0:
                    dumpSubRecords(data[4:], offset + 5 + 4)
                else:
                    print(hexdump(data, length=16, indent=8))
            elif rTlen > 0:
                print(hexdump(data, length=16, indent=8))
            offset += 5 + rXlen + rLen
        elif rType == 0x2:
            #some audio record, data but not subrecords
            print(hexdump(data, length=16, indent=8))
            offset += 5 + rXlen + rLen
        elif rType == 0x8:

            #skip the record header, (record len should be 0)
            offset += 5

            #read the next 9 bytes
            op, dummy, skipLen = struct.unpack("<B4sL", buf[offset:offset+9])
            offset += 9

            print("----Skiplen is %#x bytes, op %#x" % (skipLen, op))

            if op == 3:
                offset += 0x18 + skipLen
            else:
                offset += skipLen
        else:
            #this record is typically length 0, but the code skips a fixed
            #offset based on version, atcreply.dll 0x1002B17A
            if version < 0x401:
                offset += 9
            else:
                offset += 0x24

    print "\nFinished with records @ offset %#x (end @%#x)" % (offset, end)

if __name__ == "__main__":

    if len(sys.argv) < 2:
        print "Usage: %s <wrf file>" % (sys.argv[0])
        sys.exit(1)

    wrfFile = open(sys.argv[1], "rb")
    wrfBuf = wrfFile.read()
    wrfFile.close()

    print "Dumping WRF file size %#x (%#d)\n" % (len(wrfBuf), len(wrfBuf))

    curOffset, keyFrameOffset, version = readHeader(wrfBuf)

    curOffset = readKeyFrame(wrfBuf, keyFrameOffset, version)

    dumpRecords(wrfBuf, curOffset, version)
