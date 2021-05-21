import django
import dask
import dask.distributed as dd


import ever_given.wrapper

from core.models import (
    AnswerKey,
    Evaluation,
    FloatValue,
    InputElement,
    InputValue,
    Prediction,
    Submission,
    SubmissionRun,
)

# should this happen on the module level or in the function/method?
# django.setup()


def score_submission(submission_id, *run_ids):

    submission = Submission.objects.get(pk=submission_id)
    challenge = submission.challenge
    smiles_type = challenge.inputtype_set.get(key="SMILES")
    for run_id in run_ids:

        submission_run = submission.submissionrun_set.get(pk=run_id)
        evaluations = submission_run.evaluation_set.all()
        for evaluation in evaluations:
            prediction = evaluation.prediction_set.get(key="molWeight")
            input_element = evaluation.input_element
            input_value = input_element.inputvalue_set.get(input_type=smiles_type)

            answer_key = challenge.answerkey_set.get(
                input_element=input_element, key="molWeight"
            )
            print(
                "Prediction:",
                prediction.value,
                input_value.value,
                "answer:",
                answer_key.value,
            )


def get_status(key):
    dask_url = "127.0.0.1:8786"
    client = dd.Client(dask_url)
    return client.get_metadata(key)


def run_and_score_submission(client, submission):
    """
    Runs public and private, plus scoring
    """
    #    dask_url = "127.0.0.1:8786"
    #    client = dd.Client(dask_url)  # , asynchronous=True)
    challenge = submission.challenge
    public_element_ids = challenge.inputelement_set.filter(is_public=True).values_list(
        "id", flat=True
    )
    private_element_ids = challenge.inputelement_set.filter(
        is_public=False
    ).values_list("id", flat=True)

    public_run_id, public_prediction_ids = run_submission(
        submission.pk, public_element_ids, True, is_public=True
    )
    public_success = check_and_score(public_run_id, public_prediction_ids)
    private_run_id, private_prediction_ids = run_submission(
        submission.pk, private_element_ids, public_success, is_public=False
    )

    private_success = check_and_score(private_run_id, private_prediction_ids)
    private_success.visualize(filename="delayed_graph.svg")
    future = client.submit(private_success.compute)
    print("Future key:", future.key)

    dd.fire_and_forget(future)
    return future


@dask.delayed(pure=False)
def check_and_score(submission_run_id, prediction_ids):
    submission_run = SubmissionRun.objects.get(pk=submission_run_id)
    submission_run.status = SubmissionRun._Status.SUCCESS
    submission_run.save()
    print(
        "Running check_and_score",
        submission_run_id,
        "public?",
        submission_run.is_public,
    )
    return True


@dask.delayed(pure=False)
def chain(upstream_success, delayed_func, *args, **kwargs):
    # Can ignore upstream_success
    return delayed_func(*args, **kwargs)


@dask.delayed(pure=False)
def create_submission_run(submission_id, conditional, is_public=True):
    # conditional will be a dask delayed; if it's false, the run_element will no-op
    if not conditional:
        return
    from django.conf import settings

    submission = Submission.objects.get(pk=submission_id)
    container = submission.container
    if not container.digest:
        container.digest = "DEADBEEF"
        container.save()
    submission_run = SubmissionRun.objects.create(
        submission=submission,
        digest=container.digest,
        is_public=is_public,
        status=SubmissionRun._Status.PENDING,
    )
    # TODO: need to store future key?
    # submission run pair is place to store?
    # submission_run.digest = future.key
    submission_run.save()
    return submission_run.id


def run_submission(submission_id, element_ids, conditional, is_public=True):

    submission_run_id = create_submission_run(
        submission_id, conditional, is_public=is_public
    )
    delayeds = dask.delayed(
        [
            run_element(
                submission_id,
                element_id,
                submission_run_id,
                is_public=is_public,
            )
            for element_id in element_ids
        ],
        nout=len(element_ids),
    )
    return (submission_run_id, delayeds)


def OBSrun_all_elements(submission_id, submission_run_id):

    submission = Submission.objects.get(pk=submission_id)
    challenge = submission.challenge
    submission_run = submission.submissionrun_set.get(pk=submission_run_id)
    input_elements = challenge.inputelement_set.filter(
        is_public=submission_run.is_public
    )
    args = [
        (submission.id, input_element.id, submission_run.id)
        for input_element in input_elements
    ]
    print("about to submit!")
    with dd.worker_client() as client:
        futures = client.map(run_element, args, pure=False)

        print("futures", futures)
        print("About to gather")
        # when do we "know" it was a success?
        runs = client.gather(futures)
    submission_run.status = SubmissionRun._Status.SUCCESS
    submission_run.save()
    print(runs)


@dask.delayed(pure=False)
def run_element(submission_id, element_id, submission_run_id, is_public):
    submission = Submission.objects.get(pk=submission_id)
    challenge = submission.challenge
    submission_run = submission.submissionrun_set.get(pk=submission_run_id)
    element = challenge.inputelement_set.get(pk=element_id, is_public=is_public)

    container = submission.container

    evaluation = Evaluation.objects.create(
        input_element=element, submission_run=submission_run, exit_status=1
    )
    container_uri = f"{container.registry}/{container.label}:{container.tag}"
    smiles_string = InputValue.objects.get(input_element=element).value
    try:
        command = submission.challenge.execution_options_json["command"]
        command += smiles_string
    except KeyError:  # if no execution options nothing to prepend
        command = smiles_string
    print(command)
    result = ever_given.wrapper.run_submission_container(container_uri, command)
    result = float(result.strip())
    print(result)
    result_obj = FloatValue.objects.create(value=result)
    # maybe we return the prediction so we can score it?
    prediction = Prediction.objects.create(
        challenge=challenge,
        key="molWeight",
        evaluation=evaluation,
        value_object=result_obj,
    )
    evaluation.exit_status = 0
    evaluation.save()
    return prediction.pk
