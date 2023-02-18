export CUDA_VISIBLE_DEVICES=0,1,2,3
python3 -m torch.distributed.launch --nproc_per_node=4 --master_port=6020 hugnlp_runner.py \
  --model_name_or_path=/wjn/pre-trained-lm/Erlangshen-MegatronBert-1.3B \
  --data_dir=/wjn/competition/clue/datasets/merge \
  --output_dir=./outputs/merge \
  --seed=42 \
  --exp_name=cpic-clue-wjn \
  --max_seq_length=512 \
  --max_eval_seq_length=512 \
  --do_train \
  --per_device_train_batch_size=2 \
  --per_device_eval_batch_size=12 \
  --gradient_accumulation_steps=4 \
  --evaluation_strategy=no \
  --save_strategy=steps \
  --learning_rate=2e-05 \
  --num_train_epochs=2 \
  --logging_steps=100000000 \
  --save_steps=6000 \
  --save_total_limit=6 \
  --warmup_steps=2000 \
  --report_to=none \
  --task_name=clue_mrc_style \
  --task_type=global_pointer \
  --model_type=bert \
  --metric_for_best_model=macro_f1 \
  --pad_to_max_length=True \
  --remove_unused_columns=False \
  --fp16 \
  --label_names=short_labels \
  --keep_predict_labels \
  --dataloader_num_workers=1 \
  --preprocessing_num_workers=1 \
  --user_defined="data_name=clue" \
  --sharded_ddp=zero_dp_2