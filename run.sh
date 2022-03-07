outputdir='path/to/output/dir'
aishell4text='path/to/textgridlist/file'
aishell4wav='path/to/wavlist/file'

if [ ! -d $outputdir ];then
  mkdir -p $outputdir
fi

python -u grep_aishell4_multi_spk.py  --output_dir $outputdir \
         --aishell4_wav_list $aishell4wav --textgrid_list $aishell4text  \
         --overlap_spk_tolerance  2  --overlap_tolerance 10 --overrate_tolerance 0.1 \
         --adjacent_segments 4  --sil_tolerance 1000
