import os
import shutil
from pathlib import Path
import concurrent.futures
import time
import tqdm

def copy_practice_dir_worker(source_practice_dir: Path, dest_practice_dir: Path):
    """
    Worker thread function for copying a single code program directory.
    Designed to run in a thread.
    """
    try:
        dest_practice_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source_practice_dir, dest_practice_dir)
        return None
    except FileExistsError:
        return None
    except Exception as e:
        return e

def copy_all_practices_multithreaded(original_dname: Path, dirname: Path, max_workers: int = None):
    """
    Use multithreaded copy of 'exercises/practice' subdirectories from original_dname to dirname.

    Parameters:
        original_dname: source base directory (Path object)
        dirname: destination base directory (Path object)
        max_workers: maximum number of threads, default is the reasonable value selected by ThreadPoolExecutor
    """
    if not isinstance(original_dname, Path):
        original_dname = Path(original_dname)
    if not isinstance(dirname, Path):
        dirname = Path(dirname)

    if dirname.exists():
        print(f"destination directory {dirname} already exists, skipping copy.")
        return

    print(f"preparing to copy from {original_dname} to {dirname}, using multithreading...")
    dirname.mkdir(parents=True, exist_ok=True)

    tasks = []
    for lang_dir in original_dname.iterdir():
        if not lang_dir.is_dir():
            continue

        practice_dir = lang_dir / "exercises" / "practice"
        if practice_dir.exists() and practice_dir.is_dir():
            dest_practice_dir = dirname / lang_dir.name / "exercises" / "practice"
            practice_code_programs = [practice_code_program for practice_code_program in practice_dir.iterdir()]
            for practice_code_program in practice_code_programs:
                tasks.append((practice_code_program, dest_practice_dir / practice_code_program.name))

    if not tasks:
        print("no 'exercises/practice' directories found to copy.")
        print("...completed")
        return

    print(f"found {len(tasks)} code program directories, starting multithreaded copy...")
    start_time = time.time()

    pbar = tqdm.tqdm(total=len(tasks), desc="copy code program")

    successful_copies = 0
    failed_copies = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_task = {executor.submit(copy_practice_dir_worker, src, dest): (src, dest) for src, dest in tasks}

        for future in concurrent.futures.as_completed(future_to_task):
            src, dest = future_to_task[future]
            try:
                result = future.result()
                pbar.update(1)
                if result is None:
                    successful_copies += 1
                else:
                    failed_copies += 1
            except Exception as exc:
                print(f"  unhandled exception, error copying {src} to {dest}: {exc}")
                failed_copies += 1

    end_time = time.time()
    print(f"...multithreaded copy completed, time taken: {end_time - start_time:.2f} seconds.")
    print(f"summary: successfully copied {successful_copies} files, failed {failed_copies} files.")

if __name__ == "__main__":

    original_dir = Path("tmp.run_unit_test/polyglot-benchmark")
    destination_dir = Path("tmp.run_unit_test/temp_copied_exercises")

    if destination_dir.exists():
        print(f"detected old destination directory, deleting: {destination_dir}")
        shutil.rmtree(destination_dir)

    import os
    print(os.cpu_count())
    max_workers = os.cpu_count()
    copy_all_practices_multithreaded(original_dir, destination_dir, max_workers=max_workers)

    print("-" * 20)
    print("script executed, please check temp_copied_exercises directory.")
