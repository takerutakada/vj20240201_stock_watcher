import use_selenium

success, failed = 0, 0
trials_count = 0
max_trial_count = 1
while trials_count < max_trial_count:
    try:
        use_selenium.main_func()
        success += 1
    except:
        failed += 1
        continue
    trials_count += 1
    print(trials_count)

print(f'success: {success} / failed: {failed}')
