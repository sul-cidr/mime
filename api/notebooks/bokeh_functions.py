from datetime import datetime
from functools import partial
import numpy as np


from bokeh.layouts import column, row
from bokeh.models import (
    Button,
    CrosshairTool,
    DatetimeTickFormatter,
    Div,
    LinearAxis,
    Range1d,
    Slider,
    Span,
    TapTool,
    Toggle,
)
from bokeh.plotting import figure

from pose_functions import *


def pil_to_bokeh_image(pil_img, target_width, target_height):
    """
    The Bokeh interactive notebook tools will only display image data if it's formatted
    in a particular way
    """
    img_array = np.array(pil_img.transpose(Image.Transpose.FLIP_TOP_BOTTOM))

    img = np.empty(img_array.shape[:2], dtype=np.uint32)
    view = img.view(dtype=np.uint8).reshape(img_array.shape)

    for i in range(target_height):
        for j in range(target_width):
            view[i, j, 0] = img_array[i, j, 0]
            view[i, j, 1] = img_array[i, j, 1]
            view[i, j, 2] = img_array[i, j, 2]
            view[i, j, 3] = img_array[i, j, 3]

    return img


def build_bokeh_app(
    pose_series,
    pose_data,
    normalized_pose_data,
    normalized_pose_metadata,
    pose_angle_data,
    video_file,
    video_width,
    video_height,
    video_fps,
    faiss_ip_index,
):
    """Returns a function to run the Bokeh app in a Jupyter notebook environment"""

    def bkapp(doc):
        """Define and run the Bokeh interactive notebook (Python + Javascript) application"""

        # Some session data is best stored in a global dictionary
        data = {}

        comparison_poses = [{}, {}]

        max_y = max(pose_series["avg_coords_per_pose"] + pose_series["num_poses"])

        # This is the main interactive timeline chart
        tl = figure(
            width=FIGURE_WIDTH,
            height=FIGURE_HEIGHT,
            title=video_file,
            min_border=10,
            y_range=(0, max_y + 1),
            tools="save,box_zoom,pan,reset",
        )
        # Format the X axis as hour-minute-second timecodes
        tl.x_range = Range1d(
            min(pose_series["timestamp"]), max(pose_series["timestamp"])
        )
        tl.xaxis.axis_label = "Time"
        time_formatter = DatetimeTickFormatter(
            hourmin="%H:%M:%S",
            minutes="%H:%M:%S",
            minsec="%H:%M:%S",
            seconds="%Ss",
            milliseconds="%3Nms",
        )
        # The 3 main pose-related time series to be visualized on the timeline
        tl.line(
            pose_series["timestamp"],
            pose_series["num_poses"],
            legend_label="Poses per frame",
            color="blue",
            alpha=0.6,
            line_width=2,
        )
        tl.line(
            pose_series["timestamp"],
            pose_series["avg_coords_per_pose"],
            legend_label="Coords per pose",
            color="red",
            alpha=0.6,
            line_width=2,
        )
        # Only display this if figure tracking has been run
        if "tracked_poses" in pose_series:
            tl.line(
                pose_series["timestamp"],
                pose_series["tracked_poses"],
                legend_label="Tracked poses",
                color="purple",
                alpha=0.6,
                line_width=2,
            )
        tl.line(
            pose_series["timestamp"],
            [0] * len(pose_series["frame"]),
            color="orange",
            alpha=0,
            line_width=2,
            name="similar_poses",
        )
        # Only display this if scene/activity detection has been run
        if "activity" in pose_series:
            tl.line(
                pose_series["timestamp"],
                pose_series["activity"],
                y_range_name="avg_score",
                legend_label="Activity",
                color="black",
                alpha=0.6,
                line_width=1,
                name="activity",
            )

        # The left Y axis corresponds to counts of poses and coordinates
        tl.yaxis.axis_label = "Poses or Coords"
        tl.extra_y_ranges = {"avg_score": Range1d(0, 1)}
        tl.line(
            pose_series["timestamp"],
            pose_series["avg_score"],
            y_range_name="avg_score",
            legend_label="Avg pose score",
            color="green",
            alpha=0.4,
            line_width=2,
        )
        # The right Y axis corresponds to the average pose score (from 0 to 1), and to the
        # per-frame similarity score (0 to 1) when a pose search query has been run.
        tl.add_layout(
            LinearAxis(
                y_range_name="avg_score",
                axis_label="Avg Pose Score or Cosine Similarity",
            ),
            "right",
        )
        tl.xaxis.formatter = time_formatter
        tl.xaxis.ticker.desired_num_ticks = 10
        tl.legend.click_policy = "hide"
        frame_line = Span(
            location=pose_series["timestamp"][0],
            dimension="height",
            line_color="red",
            line_width=3,
        )
        tl.add_layout(frame_line)

        def tl_tap(event):
            """When the chart is clicked, move the slider to the appropriate frame"""
            # Do not respond to clicks on the top 25% of the plot. This is to try inadvertently
            # selecting a new frame when the user just wants to click on the legend to hide or
            # show one of the time-series glyphs.
            if event.y > 0.75 * max_y:
                return
            # event.x is a timestamp, so it needs to be converted to a frameno
            start_dt = datetime(1900, 1, 1)
            dt = datetime.utcfromtimestamp(event.x / 1000)
            t_delta = dt - start_dt
            clicked_frame = (
                round(t_delta.total_seconds() * video_fps) + 1
            )  # Slider framenos are 1-indexed
            slider_callback(None, slider.value, clicked_frame)

        tl_tap_tool = TapTool()
        tl_crosshair_tool = CrosshairTool()

        def get_frame_info(fn):
            frame_dt = pose_series["timestamp"][fn]
            frame_tc = frame_dt.strftime("%H:%M:%S.%f")[:-4]
            return f"{frame_tc}: {pose_series['num_poses'][fn]} detected poses, {pose_series['tracked_poses'][fn]} tracked, {pose_series['avg_coords_per_pose'][fn]:.3f} avg coords/pose, {pose_series['avg_score'][fn]:.3f} avg pose score"

        info_div = Div(text=get_frame_info(0))

        tl.add_tools(tl_tap_tool, tl_crosshair_tool)
        tl.on_event("tap", tl_tap)

        # This is the second figure, where the poses in the selected frame are drawn
        fr = figure(
            x_range=(0, video_width),
            y_range=(0, video_height),
            width=FIGURE_WIDTH,
            height=int(FIGURE_WIDTH / video_width * video_height),
            title="Poses in selected frame",
            tools="save",
        )
        # Add an invisible glyph to suppress the "figure has no renderers" warning
        fr.circle(0, 0, size=0, alpha=0.0)

        pose_info_div = Div(text="Click to poses to compare")

        # This is the drawing of the first pose selected from a frame
        pose_p1 = figure(
            x_range=(0, POSE_MAX_DIM),
            y_range=(0, POSE_MAX_DIM),
            width=POSE_MAX_DIM * 2,
            height=POSE_MAX_DIM * 2,
            title="",
            tools="",
        )
        # Add an invisible glyph to suppress the "figure has no renderers" warning
        pose_p1.circle(0, 0, size=0, alpha=0.0)

        # This is the second pose selected from a frame
        pose_p2 = figure(
            x_range=(0, POSE_MAX_DIM),
            y_range=(0, POSE_MAX_DIM),
            width=POSE_MAX_DIM * 2,
            height=POSE_MAX_DIM * 2,
            title="",
            tools="",
        )
        # Add an invisible glyph to suppress the "figure has no renderers" warning
        pose_p2.circle(0, 0, size=0, alpha=0.0)

        def background_toggle_handler(event):
            """When the image underlay is toggled, prompt the slider to redraw the frame"""
            slider_callback(None, slider.value, slider.value)

        background_switch = Toggle(label="show background", active=False)
        background_switch.on_click(background_toggle_handler)

        def slider_callback(attr, old, new):
            """
            When the slider moves, draw the poses in the new frame and show the background
            if desired. Also erase the selected pose drawings and the search results (not
            sure this is desirable).
            """
            slider.value = new
            fr.renderers = []
            if background_switch.active:
                rgba_bg = image_from_video_frame(video_file, new - 1)
                pil_bg = Image.fromarray(rgba_bg)
                frame_img = draw_frame(
                    pose_data[new - 1], video_width, video_height, pil_bg
                )
            else:
                frame_img = draw_frame(pose_data[new - 1], video_width, video_height)
            img = pil_to_bokeh_image(frame_img, video_width, video_height)
            fr.image_rgba(image=[img], x=0, y=0, dw=img.shape[1], dh=img.shape[0])
            if old != new:
                info_div.text = get_frame_info(new - 1)
                frame_line.location = pose_series["timestamp"][new - 1]

        slider = Slider(
            start=1, end=len(pose_data), value=1, step=1, title="Selected frame"
        )
        slider.on_change("value_throttled", slider_callback)

        def get_pose_extent_maps(frameno):
            """
            Determine the regions around each pose drawn on the frame that can be clicked
            to select them.
            """
            pose_extent_maps = []
            for i, pose_prediction in enumerate(pose_data[frameno]["predictions"]):
                if "bbox" in pose_prediction:
                    bbox = pose_prediction["bbox"]
                else:
                    extent = get_pose_extent(pose_prediction)
                    bbox = [
                        extent[0],
                        extent[1],
                        extent[2] - extent[0],
                        extent[3] - extent[1],
                    ]

                extent_map = {
                    "poseno": i,
                    "min_x": bbox[0],
                    "min_y": video_height - bbox[3] - bbox[1],
                    "max_x": bbox[0] + bbox[2],
                    "max_y": video_height - bbox[1],
                }

                pose_extent_maps.append(extent_map)

            return pose_extent_maps

        def match_pose_pixel_maps(x, y, pose_extent_maps):
            """
            When an x,y coordinate on the frame is clicked, check the regions calculated in
            get_pose_extent_maps() to see if the user wants to select one (or more) of the
            poses in the frame.
            """
            matched_poses = []
            for extent_map in pose_extent_maps:
                if (
                    x >= extent_map["min_x"]
                    and x <= extent_map["max_x"]
                    and y >= extent_map["min_y"]
                    and y <= extent_map["max_y"]
                ):
                    matched_poses.append(extent_map["poseno"])
            return matched_poses

        def fr_tap(event):
            """
            When the frame is clicked, determine if one of the poses in the frame has
            been selected, then draw it in one of the two boxes below (if available)
            and, if there are now two poses drawn in the boxes below, calculate and
            display their cosine similarity score.
            """
            pose_extent_maps = get_pose_extent_maps(slider.value - 1)
            clicked_poses = match_pose_pixel_maps(event.x, event.y, pose_extent_maps)
            if len(clicked_poses) > 0:
                pose_img = normalize_and_draw_pose(
                    pose_data[slider.value - 1]["predictions"][clicked_poses[0]],
                    video_file,
                )
                pose_img = pil_to_bokeh_image(pose_img, POSE_MAX_DIM, POSE_MAX_DIM)

                if pose_p1.title.text == "" or not comparison_poses[0]:
                    comparison_poses[0] = {
                        "frameno": slider.value - 1,
                        "poseno": clicked_poses[0],
                    }

                    pose_p1.image_rgba(
                        image=[pose_img],
                        x=0,
                        y=0,
                        dw=pose_img.shape[1],
                        dh=pose_img.shape[0],
                    )
                    pose_p1.title = f"{clicked_poses[0]+1}"
                    pose_info_div.text = "Please click another pose for comparison"

                else:
                    pose_p2.title.text = ""
                    pose_p2.renderers = []

                    comparison_poses[1] = {
                        "frameno": slider.value - 1,
                        "poseno": clicked_poses[0],
                    }

                    pose_p2.image_rgba(
                        image=[pose_img],
                        x=0,
                        y=0,
                        dw=pose_img.shape[1],
                        dh=pose_img.shape[0],
                    )
                    pose_p2.title = f"{clicked_poses[0]+1}"

                    normalized_p1 = np.nan_to_num(
                        normalized_pose_data[comparison_poses[0]["frameno"]][
                            "predictions"
                        ][comparison_poses[0]["poseno"]],
                        nan=0,
                    )
                    normalized_p2 = np.nan_to_num(
                        normalized_pose_data[comparison_poses[1]["frameno"]][
                            "predictions"
                        ][comparison_poses[1]["poseno"]],
                        nan=0,
                    )

                    cosine_similarity = compare_poses_cosine_flattened(
                        normalized_p1,
                        normalized_p2,
                    )
                    correlation_similarity = compare_poses_correlation_flattened(
                        normalized_p1,
                        normalized_p2,
                    )
                    # Note that the joint angles are indifferent to whether the pose has been normalized
                    p1_angles = pose_angle_data[comparison_poses[0]["frameno"]][
                        "predictions"
                    ][comparison_poses[0]["poseno"]]
                    p2_angles = pose_angle_data[comparison_poses[1]["frameno"]][
                        "predictions"
                    ][comparison_poses[1]["poseno"]]
                    pose_p2.title = f"{clicked_poses[0]+1}"
                    angle_similarity = compare_poses_angles(p1_angles, p2_angles)
                    pose_info_div.text = f"Similarity - Cosine (keypoints): {(cosine_similarity*100):3.3f}% | Cosine (joints): {(angle_similarity*100):3.3f}% | Correlation (keypoints): {(correlation_similarity*100):3.3f}%"

        fr_tap_tool = TapTool()

        fr.add_tools(fr_tap_tool)
        fr.on_event("tap", fr_tap)

        # Buttons to advance or back up the frame selector slider by one frame
        def prev_handler(event):
            slider_callback(None, slider.value, max(1, slider.value - 1))

        def next_handler(event):
            slider_callback(None, slider.value, min(slider.value + 1, len(pose_data)))

        prev_button = Button(label="prev")
        prev_button.on_click(prev_handler)
        next_button = Button(label="next")
        next_button.on_click(next_handler)

        search_info_div = Div(text="L2 (Euclidean distance) similar pose search")

        SIMILAR_POSES_TO_SHOW = 4
        SIMILAR_MATCHES_TO_FIND = 1000
        POSE_SIMILARITY_THRESHOLD = 0.8
        similar_poses = []

        for s in range(SIMILAR_POSES_TO_SHOW):
            similar_f = figure(
                x_range=(0, POSE_MAX_DIM),
                y_range=(0, POSE_MAX_DIM),
                width=POSE_MAX_DIM * 2,
                height=POSE_MAX_DIM * 2,
                title=f"Similar pose {s+1}",
                tools="",
            )

            def sp_tap(event, matchnum=0):
                if similar_poses[matchnum].title.text == "":
                    return
                match_frameno = int(
                    similar_poses[matchnum]
                    .title.text.split(":")[0]
                    .replace("Frame ", "")
                )
                slider_callback(None, slider.value, match_frameno)

            sp_tap_tool = TapTool()
            similar_f.add_tools(sp_tap_tool)
            similar_f.on_event("tap", partial(sp_tap, matchnum=s))
            similar_poses.append(similar_f)

        for pose_box in similar_poses:
            pose_box.circle(0, 0, size=0, alpha=0.0)

        # Need to kep track of match data for paging through all of the results
        data["match_indices"] = None
        data[
            "match_scores"
        ] = None  # These are for storing similarity results from FAISS
        data["valid_search_results"] = 0
        data["search_results_index"] = 0
        match_similarities = {}
        target_frameno = None
        target_poseno = None

        def draw_similar_poses(start_rank):
            """
            Draw up to SIMILAR_POSES_TO_SHOW in boxes below the search/query info div and
            search results paging back/forward buttons.
            """
            # Clear any previously drawn poses
            for pose_box in similar_poses:
                pose_box.renderers = []

            matches_to_show = 0
            data["search_results_index"] = start_rank

            match_framenos = []
            match_scores = []
            match_timecodes = []
            matches_advanced = 0

            while matches_to_show < SIMILAR_POSES_TO_SHOW:
                current_match_rank = matches_advanced + start_rank
                matches_advanced += 1

                match_index = data["match_indices"][current_match_rank]
                match_score = data["match_scores"][current_match_rank]
                match_frameno = normalized_pose_metadata[match_index]["frameno"]
                match_poseno = normalized_pose_metadata[match_index]["poseno"]

                # Skip the query pose if it's returned as a (100%) match. This is *usually*
                # the highest-ranked match, but may not always be so, depending on the indexing
                # process.
                if target_frameno == match_frameno and target_poseno == match_poseno:
                    continue

                matches_to_show += 1

                match_framenos.append(
                    str(match_frameno + 1)
                )  # All framenos in the UI are 1-indexed
                match_scores.append(f"{match_score:3.3f}")
                match_timecodes.append(
                    pose_series["timestamp"][match_frameno].strftime("%H:%M:%S.%f")[:-4]
                )

                if background_switch.active:
                    match_img = normalize_and_draw_pose(
                        pose_data[match_frameno]["predictions"][match_poseno],
                        video_file,
                        match_frameno,
                    )
                else:
                    match_img = normalize_and_draw_pose(
                        pose_data[match_frameno]["predictions"][match_poseno],
                        video_file,
                    )

                match_img = pil_to_bokeh_image(match_img, POSE_MAX_DIM, POSE_MAX_DIM)

                similar_poses[matches_to_show - 1].image_rgba(
                    image=[match_img],
                    x=0,
                    y=0,
                    dw=match_img.shape[1],
                    dh=match_img.shape[0],
                )
                similar_poses[
                    matches_to_show - 1
                ].title.text = f"Frame {match_frameno + 1}: {match_similarities[match_index]*100:3.3f}%"

            search_info_div.text = f"<strong>matches at</strong> {', '.join(match_timecodes)}, search index scores {', '.join(match_scores)}"

        def find_similar_poses():
            """
            Run the query against the FAISS pose vector index to find the SIMILAR_MATCHES_TO_FIND
            most similar poses to the query pose (the first pose in the comparison boxes) whose
            calculated cosine similarities are above the POSE_SIMILARITY_THRESHOLD. Note that the
            cosine similarity is (for now) calculated on the fly and used for the thresholding,
            rather than the similarity scores returned by the FAISS index (these determine the
            order in which the search results are ranked, but are relatively more difficult to
            interpret and to present to the user in an intuitive manner).
            """
            if pose_p1.title.text == "" or comparison_poses[0] is None:
                return False

            for pose_box in similar_poses:
                pose_box.renderers = []

            target_frameno = comparison_poses[0]["frameno"]
            target_poseno = comparison_poses[0]["poseno"]

            # Using normalized armature coordinates as primary features
            target_pose_w_confs = shift_normalize_rescale_pose_coords(
                pose_data[target_frameno]["predictions"][target_poseno]
            )
            target_pose = extract_trustworthy_coords(target_pose_w_confs)
            target_pose_query = np.array([np.nan_to_num(target_pose, nan=-1)]).astype(
                "float32"
            )

            # Using pose angles as primary features
            # target_pose = pose_angle_data[target_frameno]["predictions"][target_poseno]
            # target_pose_query = np.array([np.nan_to_num(target_pose, nan=-999)]).astype(
            #     "float32"
            # )

            D, I = faiss_ip_index.search(target_pose_query, SIMILAR_MATCHES_TO_FIND)

            data["match_indices"] = I[0]
            data["match_scores"] = D[0]
            data["valid_search_results"] = 0
            data["search_results_index"] = 0
            similar_frame_scores = [0] * len(pose_series["frame"])

            for m in range(SIMILAR_MATCHES_TO_FIND):
                match_index = data["match_indices"][m]
                if match_index != -1:
                    match_frameno = normalized_pose_metadata[match_index]["frameno"]
                    match_poseno = normalized_pose_metadata[match_index]["poseno"]

                    # Using normalized armature coordinates as primary features
                    comparison_similarity = compare_poses_cosine(
                        target_pose_w_confs,
                        shift_normalize_rescale_pose_coords(
                            pose_data[match_frameno]["predictions"][match_poseno]
                        ),
                    )

                    # Using pose angles as primary features
                    # match_pose = pose_angle_data[match_frameno]["predictions"][
                    #     match_poseno
                    # ]
                    # comparison_similarity = compare_poses_angles(
                    #     target_pose, match_pose
                    # )

                    match_similarities[match_index] = comparison_similarity

                    if comparison_similarity >= POSE_SIMILARITY_THRESHOLD:
                        if similar_frame_scores[match_frameno] > 0:
                            similar_frame_scores[match_frameno] = max(
                                similar_frame_scores[match_frameno],
                                comparison_similarity,
                            )
                        else:
                            similar_frame_scores[match_frameno] = comparison_similarity

                        data["valid_search_results"] += 1

            similar_poses_renderers = tl.select(name="similar_poses")
            if len(similar_poses_renderers) > 0:
                for sim_pose_renderer in similar_poses_renderers:
                    try:
                        tl.renderers.remove(sim_pose_renderer)
                    except Exception as e:
                        pass

            # Mark the frames on the video posedata timeline that have high match scores
            tl.line(
                pose_series["timestamp"],
                similar_frame_scores,
                y_range_name="avg_score",
                legend_label="Similar poses",
                color="orange",
                alpha=0.8,
                line_width=2,
                name="similar_poses",
            )

            for li in tl.legend.items:
                if li.label["value"] == "Similar poses" and li.visible is False:
                    li.visible = True

            return True

        def find_and_draw_similar_poses():
            if find_similar_poses():
                draw_similar_poses(0)

        def get_similar_poses_handler(event):
            # Need to add a tick callback to display the "please wait" message
            if pose_p1.title.text == "" or comparison_poses[0] is None:
                return
            search_info_div.text = (
                "<strong>Searching for similar poses, please wait...</strong>"
            )
            doc.add_next_tick_callback(find_and_draw_similar_poses)

        def reset_subposes_handler(event):
            """This clears both the two similarity/query pose boxes as well as the match boxes."""
            comparison_poses = [{}, {}]
            pose_p1.title.text = ""
            pose_p1.renderers = []
            pose_p2.title.text = ""
            pose_p2.renderers = []
            pose_info_div.text = ""
            for pose_box in similar_poses:
                pose_box.renderers = []
                pose_box.title.text = ""
            similar_poses_renderers = tl.select(name="similar_poses")
            if len(similar_poses_renderers) > 0:
                for sim_pose_renderer in similar_poses_renderers:
                    try:
                        tl.renderers.remove(sim_pose_renderer)
                    except Exception as e:
                        print("ERROR: unable to clear similar poses renderers")
                        pass
            for li in tl.legend.items:
                if li.label["value"] == "Similar poses":
                    li.visible = False
            search_info_div.text = "L2 (Euclidean distance) similar pose search"

        reset_subposes_button = Button(label="clear")
        reset_subposes_button.on_click(reset_subposes_handler)

        get_similar_poses_button = Button(label="look up 1st pose")
        get_similar_poses_button.on_click(get_similar_poses_handler)

        frame_control_row = row(children=[prev_button, next_button, background_switch])

        pose_buttons_column = column(reset_subposes_button, get_similar_poses_button)

        subposes_row = row(children=[pose_p1, pose_p2, pose_buttons_column])

        # Buttons to page through the search matches in groups of SIMILAR_POSES_TO_SHOW
        def prev_similar_poses_handler(event):
            draw_similar_poses(
                max(0, data["search_results_index"] - SIMILAR_POSES_TO_SHOW)
            )

        def next_similar_poses_handler(event):
            draw_similar_poses(
                min(
                    data["search_results_index"] + SIMILAR_POSES_TO_SHOW,
                    data["valid_search_results"] - SIMILAR_POSES_TO_SHOW,
                )
            )

        prev_similar_button = Button(label="previous group of poses")
        prev_similar_button.on_click(prev_similar_poses_handler)

        next_similar_button = Button(label="next group of poses")
        next_similar_button.on_click(next_similar_poses_handler)

        similar_poses_controls = row(
            children=[prev_similar_button, next_similar_button]
        )

        similar_poses_row = row(children=similar_poses)

        layout_column = column(
            tl,
            slider,
            info_div,
            frame_control_row,
            fr,
            pose_info_div,
            subposes_row,
            search_info_div,
            similar_poses_controls,
            similar_poses_row,
        )

        doc.add_root(layout_column)

    return bkapp
