# Nikita Akimov
# interplanety@interplanety.org
#
# GitHub
#   https://github.com/Korchy/blender-timeme

import bpy
import datetime
from . import datetimeex
from bpy.app.handlers import persistent
import os


class TimeMe(bpy.types.Operator):
    bl_idname = 'timeme.start'
    bl_label = 'TimeMe: Start'
    bl_description = 'Start monitor my time'

    status = None
    eventslist = []
    time = datetime.datetime.now()
    check_interval = 1  # sec
    work_time_damping = 10  # sec

    def modal(self, context, event):
        if self.status:
            if event.type not in self.eventslist:
                self.eventslist.append(event.type)
            if datetime.datetime.now() - datetime.timedelta(seconds=self.check_interval) > self.time:
                # whole time
                catitem = __class__.getcat('ALL TIME')
                catitem.cattime += (datetime.datetime.now() - self.time).total_seconds()
                catitem.cattime_str = datetimeex.DateTimeEx.deltatimetostrDHMS(catitem.cattime)
                # work time
                is_work = False
                for event in self.eventslist:
                    if event not in ['NONE', 'WINDOW_DEACTIVATE'] and event[:5] not in ['TIMER', 'NDOF_']:
                        is_work = True
                if is_work:
                    catitem = __class__.getcat('WORK TIME')
                    if datetime.datetime.now() - datetime.timedelta(seconds=self.work_time_damping) > self.time:
                        catitem.cattime += self.work_time_damping
                    else:
                        catitem.cattime += (datetime.datetime.now() - self.time).total_seconds()
                    catitem.cattime_str = datetimeex.DateTimeEx.deltatimetostrDHMS(catitem.cattime)
                # reset
                self.time = datetime.datetime.now()
                del self.eventslist[:]
            __class__.redraw()
            return {'PASS_THROUGH'}
        else:
            return {'FINISHED'}

    def execute(self, context):
        if self.status:     # double run
            return {'FINISHED'}
        if self not in bpy.context.window_manager.items():
            context.window_manager.modal_handler_add(self)
        __class__.start()
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        __class__.stop()
        return None

    @classmethod
    def clear(cls):
        bpy.context.scene.timeMeVars.cats.clear()

    @classmethod
    def start(cls):
        if not cls.status:
            bpy.types.Scene.timeMeVars = bpy.props.PointerProperty(type=TimeMeVars)
            cls.time = datetime.datetime.now()
            if TimeMe.onrender_init not in bpy.app.handlers.render_init:
                bpy.app.handlers.render_init.append(TimeMe.onrender_init)
            if TimeMe.onrender_complete not in bpy.app.handlers.render_complete:
                bpy.app.handlers.render_complete.append(TimeMe.onrender_complete)
            if TimeMe.onrender_cancel not in bpy.app.handlers.render_cancel:
                bpy.app.handlers.render_cancel.append(TimeMe.onrender_cancel)
            cls.getcat('ALL TIME')
            cls.status = 'RUNNING'

    @classmethod
    def stop(cls):
        cls.status = None
        if TimeMe.onrender_init in bpy.app.handlers.render_init:
            bpy.app.handlers.render_init.remove(TimeMe.onrender_init)
        if TimeMe.onrender_complete in bpy.app.handlers.render_complete:
            bpy.app.handlers.render_complete.remove(TimeMe.onrender_complete)
        if TimeMe.onrender_cancel in bpy.app.handlers.render_cancel:
            bpy.app.handlers.render_cancel.remove(TimeMe.onrender_cancel)
        if hasattr(bpy.types.Scene, 'timeMeVars'):
            del bpy.types.Scene.timeMeVars

    @staticmethod
    def getcat(catname):
        for cat in bpy.context.scene.timeMeVars.cats:
            if cat.catname == catname:
                return cat
        newcat = bpy.context.scene.timeMeVars.cats.add()
        newcat.catname = catname
        newcat.cattime = datetime.timedelta().total_seconds()
        newcat.cattime_str = datetimeex.DateTimeEx.deltatimetostrDHMS(newcat.cattime)
        return newcat

    @staticmethod
    def gettext():
        text = '='*50 + '\n'
        text += '= Counting this project time by TimeMe = \n'
        text += '='*50 + '\n'
        text += 'PROJECT: ' + os.path.splitext(os.path.basename(bpy.data.filepath))[0] + '\n'
        for cat in bpy.context.scene.timeMeVars.cats:
            text += (cat.catname + ': ' + cat.cattime_str)+'\n'
        text += '='*50
        return text

    @classmethod
    def onrender_init(cls, scene):
        cls.time_render = datetime.datetime.now()

    @classmethod
    def onrender_complete(cls, scene):
        catitem = cls.getcat('RENDER TIME')
        catitem.cattime += (datetime.datetime.now() - cls.time_render).total_seconds()
        catitem.cattime_str = datetimeex.DateTimeEx.deltatimetostrDHMS(catitem.cattime)
        __class__.redraw()
        delattr(cls, 'time_render')

    @classmethod
    def onrender_cancel(cls, scene):
        catitem = cls.getcat('RENDER TIME')
        catitem.cattime += (datetime.datetime.now() - cls.time_render).total_seconds()
        catitem.cattime_str = datetimeex.DateTimeEx.deltatimetostrDHMS(catitem.cattime)
        __class__.redraw()
        delattr(cls, 'time_render')

    @staticmethod
    def redraw():
        areas = bpy.context.screen.areas if bpy.context.screen else bpy.data.window_managers[0].windows[0].screen.areas
        for area in areas:
            area.tag_redraw()


class TimeMePrint(bpy.types.Operator):
    bl_idname = 'timeme.print'
    bl_label = 'TimeMe: Print'

    def execute(self, context):
        if 'TimeMe' in bpy.data.texts:
            textObj = bpy.data.texts['TimeMe']
        else:
            textObj = bpy.data.texts.new(name='TimeMe')
        textObj.from_string(TimeMe.gettext())
        textObj.name = 'TimeMe'
        areatoshow = None
        for area in bpy.context.screen.areas:
            if area.type == 'TEXT_EDITOR':
                areatoshow = area
        if not areatoshow:
            for area in bpy.context.screen.areas:
                if area.type not in ['PROPERTIES', 'INFO', 'OUTLINER']:
                    areatoshow = area
                    break
        if areatoshow:
            areatoshow.type = 'TEXT_EDITOR'
            areatoshow.spaces.active.text = bpy.data.texts['TimeMe']
            bpy.data.texts['TimeMe'].current_line_index = 0
        return {'FINISHED'}


class TimeMeToClipboard(bpy.types.Operator):
    bl_idname = 'timeme.toclipboard'
    bl_label = 'TimeMe: ToClipboard'

    def execute(self, context):
        bpy.context.window_manager.clipboard = TimeMe.gettext()
        return {'FINISHED'}


class TimeMeReset(bpy.types.Operator):
    bl_idname = 'timeme.reset'
    bl_label = 'Are you sure?'

    def execute(self, context):
        TimeMe.clear()
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=90)

class TimeMeCatsItem(bpy.types.PropertyGroup):
    catname = bpy.props.StringProperty(name='catname', default='')
    cattime = bpy.props.FloatProperty(name='cattime')
    cattime_str = bpy.props.StringProperty(name='cattime')


class TimeMeVars(bpy.types.PropertyGroup):
    cats = bpy.props.CollectionProperty(type=TimeMeCatsItem, name='cats')
    activecat = bpy.props.IntProperty(name='activecat', default=-1)


@persistent
def onsceneload_post(scene):
    bpy.ops.timeme.start()

@persistent
def onsceneload_pre(scene):
    TimeMe.stop()


def register():
    bpy.utils.register_class(TimeMe)
    bpy.utils.register_class(TimeMePrint)
    bpy.utils.register_class(TimeMeToClipboard)
    bpy.utils.register_class(TimeMeReset)
    bpy.utils.register_class(TimeMeCatsItem)
    bpy.utils.register_class(TimeMeVars)
    if onsceneload_pre not in bpy.app.handlers.load_pre:
        bpy.app.handlers.load_pre.append(onsceneload_pre)
    if onsceneload_post not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(onsceneload_post)


def unregister():
    TimeMe.stop()
    if onsceneload_pre in bpy.app.handlers.load_pre:
        bpy.app.handlers.load_pre.remove(onsceneload_pre)
    if onsceneload_post in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(onsceneload_post)
    bpy.utils.unregister_class(TimeMe)
    bpy.utils.unregister_class(TimeMeReset)
    bpy.utils.unregister_class(TimeMeToClipboard)
    bpy.utils.unregister_class(TimeMePrint)
    bpy.utils.unregister_class(TimeMeCatsItem)
    bpy.utils.unregister_class(TimeMeVars)
