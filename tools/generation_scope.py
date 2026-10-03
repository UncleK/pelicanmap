"""Source-reviewed generation process, never inferred from a media extension."""
import re

DIRECT_VIDEO_MODELS = re.compile(r'^(?:veo(?:[ -]?\d+(?:\.\d+)?)?|sora(?:[ -]?\d+(?:\.\d+)?)?)(?:\s|$)', re.I)
DIRECT_VIDEO_IDS = {
    'x-1866187975148929474-7e2d12f3',
    'x-1868801821101437107-fbc3a18f',
    'x-1925333644555452774-64006dea',
    'x-1938281396759642489-1db35b96',
}


def require_code_generation(method, evidence, model):
    """New intake requires explicit source evidence, not 'video means generated'."""
    if method != 'code-generated':
        raise ValueError('New works must be source-reviewed LLM code-generated outputs, not direct text-to-video')
    if DIRECT_VIDEO_MODELS.search(str(model)):
        raise ValueError('A direct video model output is not an LLM code-generated artwork')
    if not isinstance(evidence, list) or not evidence or not all(isinstance(x, str) and x.startswith('https://') for x in evidence):
        raise ValueError('Code-generation source evidence is required; media format or model label is not evidence')


def is_direct_video(item):
    """Preserved reviewed legacy IDs or an explicit process label only."""
    return item.get('id') in DIRECT_VIDEO_IDS or item.get('generationMethod') == 'direct-text-to-video'
