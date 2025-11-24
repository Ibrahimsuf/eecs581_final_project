from flask import Blueprint, request, jsonify
from database_helpers import mark_applied, unmark_applied, get_user_applied_jobs, is_job_applied_by_user

bp = Blueprint('applied_jobs', __name__)

def _get_current_user_id():
    uid = request.headers.get('X-User-Id')
    try:
        return int(uid)
    except:
        return None

@bp.route('/api/jobs/<int:job_id>/apply', methods=['POST'])
def apply_job(job_id):
    user_id = _get_current_user_id()
    if not user_id:
        return jsonify({'error': 'unauthenticated'}), 401
    data = request.get_json(silent=True) or {}
    notes = data.get('notes')
    mark_applied(user_id, job_id, notes)
    return jsonify({'applied': True}), 200

@bp.route('/api/jobs/<int:job_id>/apply', methods=['DELETE'])
def unapply_job(job_id):
    user_id = _get_current_user_id()
    if not user_id:
        return jsonify({'error': 'unauthenticated'}), 401
    unmark_applied(user_id, job_id)
    return '', 204

@bp.route('/api/me/applied-jobs', methods=['GET'])
def list_applied_jobs():
    user_id = _get_current_user_id()
    if not user_id:
        return jsonify({'error': 'unauthenticated'}), 401
    applied = get_user_applied_jobs(user_id)
    return jsonify({'applied': applied}), 200

@bp.route('/api/jobs/<int:job_id>/is-applied', methods=['GET'])
def check_applied(job_id):
    user_id = _get_current_user_id()
    if not user_id:
        return jsonify({'error': 'unauthenticated'}), 401
    applied = is_job_applied_by_user(user_id, job_id)
    return jsonify({'applied': applied}), 200
