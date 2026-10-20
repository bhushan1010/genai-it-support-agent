import csv
from scripts.summarize_study import summarize


def test_study_blank_is_not_a_result():
    assert summarize('data/eval/timed_study.csv')['trials']==0


def test_study_only_pairs_correct_comparable_trials(tmp_path):
    path=tmp_path/'study.csv'
    with path.open('w',newline='') as f:
        w=csv.writer(f)
        w.writerow(['participant_id','matched_pair_id','condition','case_id','order','correct','seconds','notes'])
        w.writerows([['p1','a','manual','x','1','1','100',''],['p1','a','assistant','y','2','1','60',''],
                     ['p2','b','manual','x','2','0','100',''],['p2','b','assistant','y','1','1','30','']])
    result=summarize(path)
    assert result['both_correct_pairs']==1
    assert result['mean_paired_time_reduction']==0.4
    assert result['accuracy']['manual']==0.5
