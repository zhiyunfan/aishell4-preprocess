outputdir='path/to/output/dir'
aishell4text='path/to/textgridlist/file'
aishell4wav='path/to/wavlist/file'

if [ ! -d $outputdir ];then
  mkdir -p $outputdir
fi

## overlap_spk_tolerance: the max number of speakers speaking at the same time
## overlap_tolerance: the max number of speaker overlapped frames in one generated sentences
## overrate_tolerance: max duration ratio of overlapped speech in any interval
## adjacent_segments: the number of intervals used to form one sentence
## sil_tolerance: the max duration of silence

python -u grep_aishell4_multi_spk.py  --output_dir $outputdir \
         --aishell4_wav_list $aishell4wav --textgrid_list $aishell4text  \
         --overlap_spk_tolerance  2  --overlap_tolerance 10 --overrate_tolerance 0.1 \
         --adjacent_segments 4  --sil_tolerance 1000
