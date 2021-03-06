from pathlib import Path
from typing import List

from dask.distributed import Client

# First we want to run the submission on the public data
# + report errors (per mol)
# Run the score container, report results
# Then we run the submission on the private data (per mol)
# score container

SUBMISSION_DIR = Path("data-submissions").resolve()

print(SUBMISSION_DIR)


def gather_mols(data_dir: str) -> List[str]:
    p = Path(data_dir)
    if p.exists() and p.is_dir():
        p = p.resolve()
        mols = list(p.glob("mol_*"))
        return mols
    else:
        raise OSError("does not exist or not a directory")


def prep_out_path(image):
    run_id = get_container_id(image)
    run_id = str(run_id)
    # slice off sha:
    run_id = run_id.split(":")[-1]
    SUBMISSION_DIR.joinpath(run_id).mkdir(parents=True, exist_ok=True)
    return run_id


def get_container_id(image):
    import docker

    client = docker.from_env()
    container = client.images.pull("localhost:5000/mmh42/sampl-test", tag="0.1")
    return container.attrs.get("RepoDigests")[0]

    # We will want to make sure we can the pull the container and can fail fast


def run_submission(image: str, mol_path: str, args: List[str], run_id: str) -> float:
    mol_name = mol_path.name
    try:
        with open(
            SUBMISSION_DIR.joinpath(run_id, f"score_{mol_name}"), "r"
        ) as score_file:
            score = score_file.readline().strip()
        print(f"cache hit {mol_name}")
        return float(score)
    except (FileNotFoundError):
        import docker

        client = docker.from_env()
        with open(mol_path, "r") as mol_file:
            mol = mol_file.readline().strip()

        command = [mol] + args
        print(f"running command: {command} on {mol_name} {mol}")
        result = client.containers.run(image, command, auto_remove=True)
        result = float(result.strip())
        with open(
            SUBMISSION_DIR.joinpath(run_id, f"score_{mol_name}"), "w"
        ) as score_file:
            score_file.write(f"{str(result)}\n")
        return result


'''
client = Client('127.0.0.1:8786')

image = "mmh42/sampl-test:0.1"
args = ["--fuzz"]
mols = gather_mols("data-public")

container_id = get_container_id(image)
print(container_id)
scores = []
submissions = []
run_id = prep_out_path(image)
for mol_path in mols:
    print(mol_path)
    submissions.append(client.submit(run_submission, image, mol_path, args, run_id))

results = client.gather(submissions)
total = sum(results)
print(f"total RMSE for {image} is {total}")
'''
Client

PUBLIC_DATA = Path("data-public").resolve()
PRIVATE_DATA = Path("data-private").resolve()
SUBMISSION_DIR = Path("data-submissions").resolve()


class Submission:
    def __init__(self, challenge_id: int):
        self.challenge_id = challenge_id
        self.challenge_data = CHALLENGE_DB[self.challenge_id]
        self.args = self.challenge_data["args"]
        self.image = self.challenge_data["image"]
        self.scoring_image = self.challenge_data["scoreing_image"]

    def prep(self):
        self._pull_image()
        self._prep_outputs()

    def _pull_image(self):
        # Prime docker to have the image
        import docker

        self.client = docker.from_env()
        # Might need to add a wait OR report progress on this
        # Could be slow for large images
        # Could also error out from http errors, need to retry
        container = self.client.images.pull(self.image)
        self.image_hash = container.attrs.get("RepoDigests")[0]

    def _get_mol_list(self, mol_path):
        if mol_path.exists() and mol_path.is_dir():
            mol_path = mol_path.resolve()
            mols = list(mol_path.glob("mol_*"))
            self.mols = mols
        else:
            raise OSError("does not exist or not a directory")

    def _prep_outputs(self):
        run_id = str(self.image_hash)
        # slice off sha:
        run_id = run_id.split(":")[-1]
        self.output_dir_public = SUBMISSION_DIR.joinpath(run_id, "public").mkdir(parents=True, exist_ok=True)
        self.output_dir_public = SUBMISSION_DIR.joinpath(run_id, "private").mkdir(parents=True, exist_ok=True)


    def _run(self, input_mol, output_dir, cache):
        mol_name = input_mol.name
        try:
            with open(
                output_dir.joinpath(f"score_{mol_name}"), "r"
            ) as score_file:
                score = score_file.readline().strip()
            print(f"cache hit {mol_name}")
            return float(score)
        except (FileNotFoundError):
            with open(input_mol, "r") as mol_file:
                mol = mol_file.readline().strip()

            command = [mol] + self.args
            print(f"running command: {command} on {mol_name} {mol}")
            result = self.client.containers.run(image, command, auto_remove=True)
            # Will want to catch an excpetion here and pass the log if done in public
            result = float(result.strip())
            with open(
                output_dir.joinpath(f"score_{mol_name}"), "w"
            ) as score_file:
                score_file.write(f"{str(result)}\n")
            return result

    def test_container(self):
        # run on public data + score
        # also return the logs publicly
        pass

    def run(self):
        # run on private data + score
        # use context manager
        pass

    def _score(self):
        pass

    def grade(self):
        # cleanup stuff
        # update db with values?
        pass


image = "mmh42/sampl-test:0.1"
challenge_id = 0
# Mock things that we should pull from DB as dictionary
CHALLENGE_DB = {
        0: {"image": image,
        "scoreing_image": "mmh42/score-submission:0.1",
        "challenge_name": "LogP",
        "args": ["--fuzz"],
        }
}
submission = Submission(challenge_id)
submission.prep()
submission.test_container()
#submission.run()
#submission.grade()
