#WRF file format overview

# Introduction #

This is a brief description of the Cisco WebEx .wrf file format. For more details, please read the code.

All of this was performed with the latest release of the WebEx Player as of 07/12/2012. I used the installer atcrecply.msi version 28.0.100.321. I've included it in the source archive here in case it disappears.


# Format Overview #

A wrf file consists of the following pieces:

  * File header
  * Optional key frame descriptor
  * Key frame
  * Array of T-L-V records

Additionally, certain types of records can contain subrecords.

# File header #

The header starts at offset 0 in the file, and looks like this:

```
0x0:BYTE sig[4];
0x4:DWORD version;
0x8: DWORD fileSize;  //not always correct?
0xc: DWORD someFrameThing;
0x10: WORD unknown1;
0x12: WORD unknown2;
0x14: WORD unknown3;
0x16: WORD hasKeyFrameOffset;
0x18: DWORD hasKeyFrameOffset2;	
0x1c: DWORD totalFrameCount
0x20: WORD extendedHeaderLen;
0x22: WORD extendedHeaderLen2;
```

  * sig is always WOTF.
  * version varies, and is used in several places throughout the code to determine the size of certain records.
  * fileSize does not always match the actual size of the file, it may reflect the size after certain a/v data is decompressed?
  * I haven't seen a file with the extended length fields, but according to the code they extend the length of the header, as they're added on to the current offset to move to the next file segment.

If hasKeyFrameOffset != 0 or hasKeyFrameOffset2 != 0, then the file has the key frame descriptor section, which comes directly after the header.

# Keyframe descriptor #

This section of the file describes where to locate the key frame, and looks like this:

```
0x0: DWORD keyframeOffset;
0x4: DWORD unknown;
```

keyFrameOffset is the offset in the file (starting after the key frame descriptor) of where to find the key frame. To find the key frame:

```
keyFrameOffset = totalHeaderLength (including xtra len fields) + sizeof(keyFrameDescriptor) + keyFrameOffset
```

# Keyframe #

The key frame varies in size depending on the file header version field. Specifically:

```
    if version < 0x401:
        size = 0x9
    else:
        size = 0x24
```

It looks like this:

```
0x0: BYTE keyframeType;	//always 7 it seems
0x1: DWORD keyframeTime;
0x5: DWORD keyframeSize;
0x9: BYTE unknown1;
0xa: BYTE the_rest[xx]	//donno
```

I haven't looked at any code that really uses these, but their names do most of the talking.

# Records #

The records start after the key frame. They look like this:

```
BYTE typeAndXLen;	low 4 bits type, high 12 bits "extra len?" (xLen = (typeAndXLen >> 4) << 0x10)
BYTE uk1;	//no clue
BYTE uk2;	//no clue
WORD len;	//"normal" length
BYTE data[len + xLen]
```

  * typeAndXlen are a bitfield, with the low 4 bytes holding the type. The high 12 bits are shifted as above, and added to the 'len' field to get the total length of the record.
  * the length is the length of the data that follows, not inclusive of header fields.
  * So, all together there are 28 bits of length

## Record Types ##

There are a few different groups of record types. The following is not perfect, as I haven't seen all of the types or reversed all of the code. Types are handled as follows.

### 1, 3, 9 ###
if data length is > 5, they contain subchunks. subchunk format is simple:

```
{
BYTE type
WORD len
}
```

In this case, len is inclusive of the header itself.

There are some caveats here, and more research is required to fully flesh this out. But I've noticed the following:

  * The first 4 bytes of the data field contain flags/indicator of some sort sort.
  * If 0 is found, the chunk definitely contains subrecords
  * If non-0 is found, the chunk **may** contain subrecords
  * 0xefca seems to indicate subrecords follow

This first 4 bytes field needs to be investigated further to determine the remaining cases. Also, it's possible that the two unknown fields in the record header indicate something.

### 2 ###

Audio data, doesn't contain subrecords.

### 8 ###

Unknown, but unfortunately the length field does not give the actual length of this record. So, in order to successfully parse the rest of the file you must skip bytes as follows:

```
read in next 9 bytes

first1 byte is used for a switch:
skip 4
next 4 are a length

switch:
1: add length to offset and read next record
3: read in 0x18 bytes, add length to offset and go
default: add length to offset and read next record
```

### all other types ###

Unknown, but again the length field is broken. Skip as follows.

if version < 0x409, then skip 9 bytes

else skip 0x24 bytes

# End #

There's a lot more to be documented, but I only had a few days and WebEx isn't super exciting.

# Bonus #

Have some helpful breakpoint locations and symbols names.

From atcrecply.dll (2028.1200.100.1000):

```
.text:1002A680 readHeaderAndChunks
.text:10021CF0 ; int __stdcall readFile(LPVOID lpBuffer, DWORD nNumberOfBytesToRead)
.text:1001EFD0 ; int __cdecl debugMsg(int, LPCWSTR, char arglist) #this is really useful function
.text:100235F0 processFileHeader
.text:10029530 ; int __stdcall storeChunk
```

From atas32.dll (2028.1201.300.500)

```
.text:60110D5A processRecordSubData
```

To enable debug output via debug strings, set:

HKEY\_CURRENT\_USER\Software\WebEx\config\TRACE\_ENABLE\_ATRECPLY => 1

There are also a lot of other debugging functionalities available if you look through other libraries. Or it looks that way at least.