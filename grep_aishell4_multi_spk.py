#!/usr/bin/env python

import io
import os
import subprocess
import linecache
import numpy as np
import soundfile as sf
import scipy.signal as ss
import random
import time
import librosa
import argparse
import textgrid
import pdb

def get_line_context(file_path, line_number):
    return linecache.getline(file_path, line_number).strip()

def sfread(fname):
    y, fs = sf.read(fname)
    if fs != 16000:
        y = librosa.resample(y, fs, 16000)
    return y

def cutwav(wav, minlen, maxlen):
    if wav.shape[0] < 16000*maxlen:
        return wav
    else:
        duration = int(random.uniform(minlen,maxlen)*16000)
        start = random.randint(0, wav.shape[0]-duration)
        wav = wav[start:start+duration]
        return wav

def timetable2seg(timetable):
    seg_list = []
    flag = 0
    for i in range(len(timetable)):
        if flag == 0 and timetable[i] == 1:
            flag = 1
            start = i
            continue

        if flag == 1 and timetable[i] == 0:
            flag = 0
            end = i - 1
            seg_list.append([start, end])
            continue

        if i == len(timetable) - 1 and flag == 1:
            end = i
            seg_list.append([start, end])
            continue

    return seg_list

def run(args):

    output_dir = args.output_dir

    if not os.path.exists(output_dir):
        os.mkdir(output_dir)
    if not os.path.exists(output_dir+'/wav'):
        os.makedirs(output_dir+'/wav')

    output_text = output_dir+'/text'
    output_text = open(output_text, 'w')
    output_utt2dur = output_dir+'/utt2dur'
    output_utt2dur = open(output_utt2dur, 'w')
    output_utt2spk = output_dir+'/utt2spk'
    output_utt2spk = open(output_utt2spk, 'w')


    wav_list = args.aishell4_wav_list
    textgrid_list = args.textgrid_list
    for textgrid_num in range(len(open(textgrid_list,'r').readlines())):
        grid = get_line_context(textgrid_list, textgrid_num + 1)
        tgridobj = textgrid.TextGrid()
        print(textgrid_num)
        tgridobj.read(grid)
        n_spk = len(tgridobj)
        conferencetime = tgridobj.maxTime
        conferencetime = float(conferencetime)
        conferencetime = '%.2f' % conferencetime
        conferencetime = float(conferencetime)
        timetable =  np.zeros([n_spk, int(conferencetime*100)])
        segmenttable = np.zeros([n_spk, int(conferencetime*100)])
        segmentslist = []
        centerlist = []
        content = []
        speaker = []
        index = 0
        for spk in range(n_spk):
            n_iterval = len(tgridobj[spk])
            #content.append([])
            #speaker.append([])
            #segment_index = 0
            for j in range(n_iterval):
                iterval = tgridobj[spk][j]
                if iterval.mark != '' and iterval.mark != ' ' and iterval.mark != '<%>' and iterval.mark != '<$>':
                    minTime = iterval.minTime
                    maxTime = iterval.maxTime
                    minTime = float(minTime)
                    maxTime = float(maxTime)
                    minTime = '%.2f' % minTime
                    maxTime = '%.2f' % maxTime
                    minTime = float(minTime)
                    maxTime = float(maxTime)
                    timetable[spk, int(minTime*100):int(maxTime*100)] = 1
                    #segmenttable[spk, int(minTime*100):int(maxTime*100)] = segment_index
                    #content[spk].append(iterval.mark)
                    #speaker[spk].append(tgridobj[spk].name)
                    #segmentslist.append([int(minTime*100), int(maxTime*100)])
                    centerlist.append({'index':index, 'center':(int(minTime*100)+int(maxTime*100))//2, 'segment':[int(minTime*100), int(maxTime*100)], 'spk':tgridobj[spk].name, 'text':iterval.mark})
                    #segment_index = segment_index + 1
                    index += 1


        sort_centerlist = sorted(centerlist, key=lambda keys:keys['center'])
        num_segments = len(sort_centerlist)

        subseg = []
        subseg_spk = []
        subseg_text = []

        if args.adjacent_segments == 1:
            segments_step = 1
        else:
            segments_step = args.adjacent_segments - 1


        for i in range(0,num_segments,segments_step):
            start = 100000000
            end = -1
            if args.adjacent_segments == 1:
                flag = True
            else:
                flag = False
            spk = ''
            text = ''
            for j in range(args.adjacent_segments):
                ij = i + j
                if ij > num_segments -1:
                    break
                segment_index = sort_centerlist[ij]["index"]
                spk_ = sort_centerlist[ij]['spk']
                text_ = sort_centerlist[ij]['text']
                segment = sort_centerlist[ij]["segment"]

                cur_timetable = timetable[:, segment[0]:segment[1]]
                spk_flag = np.sum(cur_timetable, axis=0)
                max_overlap_spk = np.max(spk_flag)

                if max_overlap_spk > args.overlap_spk_tolerance:
                    break

                speech = np.sum(spk_flag != 0)
                overlap = np.sum(spk_flag > 1)


                if overlap > args.overlap_tolerance:
                    break

                if overlap / speech > args.overrate_tolerance:
                    break

                if segment[0] < start:
                    start = segment[0]
                if segment[1] > end:
                    end = segment[1]

                text = text + text_ + '<e>'
                spk = spk + ' ' + spk_

                if j == segments_step:
                    flag = True

            if flag == True:
                sil = np.sum(np.sum(timetable[:, start:end], axis=0) == 0)
                if sil > args.sil_tolerance:
                    continue

                if end == -1:
                    continue

                subseg.append([start, end])
                subseg_spk.append(spk)
                subseg_text.append(text)


        wavpath = get_line_context(wav_list, textgrid_num + 1)
        wavid = wavpath.split('/')[-1]
        wavid = wavid.split('.wav')[0]
        y, fs = sf.read(wavpath)
        ### select channel 0
        y = y[:, 0]
        ### write subseg (wav, text, utt2dur)
        for i in range(len(subseg)):
            wavcut = y[subseg[i][0]*160:subseg[i][1]*160]
            sf.write(output_dir+'/wav/'+wavid+'-'+str(subseg[i][0]).rjust(6,'0')+'-'+str(subseg[i][1]).rjust(6,'0')+'.wav',wavcut,fs)
            spk = subseg_spk[i]
            text = subseg_text[i]
            output_text.write(wavid+'-'+str(subseg[i][0]).rjust(6,'0')+'-'+str(subseg[i][1]).rjust(6,'0')+' '+text+'\n')
            output_utt2dur.write(wavid+'-'+str(subseg[i][0]).rjust(6,'0')+'-'+str(subseg[i][1]).rjust(6,'0')+' '+str(wavcut.shape[0]/16000)+'\n')
            output_utt2spk.write(wavid+'-'+str(subseg[i][0]).rjust(6,'0')+'-'+str(subseg[i][1]).rjust(6,'0')+' '+spk+'\n')
            output_text.flush()
            output_utt2dur.flush()
            output_utt2spk.flush()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--text",
                        type=str,
                        help="text",
                        default="rawwav_list/train/text_dev")
    parser.add_argument("--output_dir",
                        type=str,
                        help="output_dir for data",
                        default="data_asr")
    parser.add_argument("--aishell4_wav_list",
                        type=str,
                        help="aishell4_wav_list to generate training data of real-recorded aishell-4 data",
                        default="rawwav_list/train/aishell4_eval.txt")
    parser.add_argument("--textgrid_list",
                        type=str,
                        help="textgrid_list",
                        default="rawwav_list/train/aishell4_textgrid.txt")
    parser.add_argument("--overlap_spk_tolerance",
                        type=int,
                        help="overlap_spk_tolerance",
                        default=2)
    parser.add_argument("--overlap_tolerance",
                        type=int,
                        help="overlap_tolerance",
                        default=10)
    parser.add_argument("--overrate_tolerance",
                        type=float,
                        help="overrate_tolerance",
                        default=0.1)
    parser.add_argument("--adjacent_segments",
                        type=int,
                        help="adjacent_segments",
                        default=1)
    parser.add_argument("--sil_tolerance",
                        type=int,
                        help="sil_tolerance",
                        default=1000)


    args = parser.parse_args()
    run(args)
    
