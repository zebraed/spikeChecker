#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

from maya import cmds


NUMERIC_TYPES = (
    "float", "double", "int", "long", "short", "byte",
    "doubleLinear", "doubleAngle"
)


def check_attr_spike(
    node_attr_dict,
    start_frame=0,
    end_frame=None,
    progress_callback=None
):
    """
    Check for spikes in an attribute over a range of frames

    Args:
        node_attr_dict (dict | list):
            Dict mapping node.attribute to threshold:
            {'pCube1.tx': 10.0, 'pSphere1.ry': 5.0}
            or a list of node.attribute strings (requires threshold parameter)

        start_frame (int): The start frame
        end_frame (int): The end frame
        progress_callback (callable): Optional callback function(frame, total)

    Returns:
        dict:
            A dictionary mapping node_attr to a list of tuples
            containing the spike frames and the previous and current values

    Example:
        # Dict format (each attribute has its own threshold)
        result = check_attr_spike(
            {'pCube1.tx': 10.0, 'pSphere1.ry': 5.0}
        )
    """
    # Convert to dict format {node_attr: threshold}
    if not isinstance(node_attr_dict, dict):
        raise TypeError(
            "node_attr_dict must be a dict or list"
        )

    result_dict = {}
    for node_attr in node_attr_dict.keys():
        if not cmds.objExists(node_attr):
            raise RuntimeError(f"Node {node_attr} does not exist")
        attr_type = cmds.getAttr(node_attr, type=True)
        if attr_type not in NUMERIC_TYPES:
            raise RuntimeError(
                f"Attribute {node_attr} is not numeric (type: {attr_type})"
            )

    if start_frame is None:
        start_frame = int(cmds.playbackOptions(q=True, minTime=True))
    if end_frame is None:
        end_frame = int(cmds.playbackOptions(q=True, maxTime=True))

    orig_time = cmds.currentTime(q=True)

    prev_vals = {
        node_attr: None for node_attr in node_attr_dict.keys()
    }
    total_frames = end_frame - start_frame + 1
    cmds.undoInfo(openChunk=True)
    viewport_pause(True)
    try:
        frame_range = range(start_frame, end_frame + 1)
        for frame_index, i_frame in enumerate(frame_range):
            cmds.currentTime(i_frame, e=True)
            for node_attr, attr_threshold in node_attr_dict.items():
                val = cmds.getAttr(node_attr)
                prev_val = prev_vals[node_attr]
                if prev_val is not None:
                    diff = abs(val - prev_val)
                    if diff > attr_threshold:
                        if node_attr not in result_dict:
                            result_dict[node_attr] = []
                        result_dict[node_attr].append(
                            (i_frame - 1, i_frame, prev_val, val, diff)
                        )
                prev_vals[node_attr] = val

            # Progress callback
            if progress_callback is not None:
                progress_callback(frame_index + 1, total_frames)
    finally:
        cmds.currentTime(orig_time, e=True)
        cmds.undoInfo(closeChunk=True)
        viewport_pause(False)

    return result_dict


def print_result(result_dict):
    """
    Print the result of the spike check

    Args:
        result_dict (dict):
            A dictionary mapping node_attr to a list of tuples
            containing the spike frames and the previous and current values
    """
    for node_attr, spike_list in result_dict.items():
        print(f"Spikes found for {node_attr}:")
        for _prev_frame, current_frame, prev_val, val, diff in spike_list:
            print(
                f"Spike at frame {current_frame}: "
                f"{prev_val} -> {val} (diff: {diff})\n"
            )

def viewport_pause(pause):
    """
    Pause or resume the viewport update

    Args:
        pause (bool): True to pause, False to resume
    """
    try:
        cmds.refresh(suspend=pause)
    except Exception:
        pass
    else:
        if not pause:
            cmds.refresh(force=True)


def list_nodeattr_from_cb():
    """
    Get node.attribute list from channel box selection

    Args:
        None

    Returns:
        list: list of "nodeName.attributeName" strings
    """
    sel = cmds.ls(sl=True, fl=True)
    if not sel:
        return []

    all_attrs = cmds.channelBox('mainChannelBox', q=True, sma=True)

    if not all_attrs:
        return []

    result = []
    for node in sel:
        for attr in all_attrs:
            node_attr = f"{node}.{attr}"
            if cmds.objExists(node_attr):
                result.append(node_attr)

    return result
